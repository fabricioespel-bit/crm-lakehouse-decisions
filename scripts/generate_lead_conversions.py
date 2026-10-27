"""Simula o sync do Salesforce depois que o time de vendas trabalhou os Leads: liga Lead → Opportunity.

O gerador original (generate_sample_data.py) não converteu nenhum Lead e usou e-mails únicos para
Leads e Contacts, então não há elo Lead → Opportunity nos dados. Este script cria os dois caminhos
que existem num Salesforce real:
  - converted: o vendedor converteu o Lead numa Opportunity já aberta (IsConverted, ConvertedOpportunityId);
  - contact_match: o vendedor não converteu, criou o Contact à mão com o mesmo e-mail e o colocou na
    Opportunity (elo só via e-mail → OpportunityContactRole).
Não toca no Salesforce: lê o backup do RAW (16/out/2026) e grava CSVs aplicados no RAW via MERGE.
Ver PLANO.md seção 7 (27/out/2026) para o desenho.
"""
import csv
import gzip
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(44)

BACKUP_DIR = Path.home() / "backups" / "crm-lakehouse-raw-20261016"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Momento do "sync" pós-conversão (fixo, para o script ser reprodutível)
SYNC_AT = "2026-10-27T09:00:00Z"

# --- Caminhos (sobre os 33 Leads com status 'Closed - Converted' e IsConverted = false) ---
N_CONVERTED = 20              # conversão de verdade
N_CONTACT_MATCH = 8           # vendedor criou o Contact à mão; o resto (5) segue sem elo nenhum
OPP_AFTER_ACQUISITION_DAYS = (3, 45)   # Opportunity aberta alguns dias depois do envio de aquisição

# --- Sujeira proposital ---
N_OPP_BEFORE_ACQUISITION = 1  # por caminho: Lead ligado a uma Opportunity aberta ANTES da aquisição
OPP_BEFORE_ACQUISITION_DAYS = (10, 60)
RATE_CONTACT_EMAIL_DIRTY = 0.25  # Contact digitado com caixa diferente do e-mail do Lead


def read_backup(table: str) -> list[dict]:
    with gzip.open(BACKUP_DIR / f"{table}.json.gz", "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def active(rows: list[dict]) -> list[dict]:
    return sorted((r for r in rows if not r["ISDELETED"]), key=lambda r: r["ID"])


def load_acquisition_dates() -> dict[str, date]:
    """Data do 1º envio de formulário por e-mail normalizado (a aquisição do Lead)."""
    acquisitions: dict[str, date] = {}
    with open(DATA_DIR / "marketing_form_submissions.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip().lower()
            submitted = datetime.fromisoformat(row["submitted_at"]).date()
            acquisitions[email] = min(submitted, acquisitions.get(email, submitted))
    return acquisitions


def opp_created(opp: dict) -> date:
    return date.fromisoformat(opp["CREATEDDATE"][:10])


def pick_opportunity(opps: list[dict], used: set[str], acquired: date | None, before: bool) -> dict:
    """Opportunity ainda livre, na janela relativa à aquisição; Lead orgânico (sem envio) aceita qualquer data."""
    free = [o for o in opps if o["ID"] not in used]
    if acquired is None:
        candidates = free
    elif before:
        low, high = OPP_BEFORE_ACQUISITION_DAYS
        candidates = [o for o in free if low <= (acquired - opp_created(o)).days <= high]
    else:
        low, high = OPP_AFTER_ACQUISITION_DAYS
        later = sorted((o for o in free if (opp_created(o) - acquired).days >= low), key=opp_created)
        candidates = [o for o in later if (opp_created(o) - acquired).days <= high] or later[:1]
    if not candidates:
        raise RuntimeError(f"Sem Opportunity livre para aquisição em {acquired} (before={before})")
    return random.choice(candidates)


def dirty_email(email: str) -> str:
    local, domain = email.split("@")
    return random.choice([f"{local.capitalize()}@{domain}", email.upper()])


def main():
    leads = active(read_backup("lead"))
    contacts = {c["ID"]: c for c in active(read_backup("contact"))}
    opportunities = active(read_backup("opportunity"))
    roles = active(read_backup("opportunitycontactrole"))
    acquisitions = load_acquisition_dates()

    contact_by_opp = {r["OPPORTUNITYID"]: r["CONTACTID"] for r in roles}
    role_count: dict[str, int] = {}
    for r in roles:
        role_count[r["CONTACTID"]] = role_count.get(r["CONTACTID"], 0) + 1

    # converted precisa de Contact Role (ConvertedContactId); contact_match precisa de um Contact que
    # esteja numa única Opportunity, para o e-mail apontar para um negócio só
    opps_with_role = [o for o in opportunities if o["ID"] in contact_by_opp]
    opps_single_contact = [o for o in opps_with_role if role_count[contact_by_opp[o["ID"]]] == 1]

    candidates = [l for l in leads if l["STATUS"] == "Closed - Converted" and not l["ISCONVERTED"]]
    random.shuffle(candidates)
    to_convert = candidates[:N_CONVERTED]
    to_contact_match = candidates[N_CONVERTED:N_CONVERTED + N_CONTACT_MATCH]
    print(f"{len(leads)} Leads, {len(candidates)} com 'Closed - Converted' sem conversão: "
          f"{len(to_convert)} convertidos, {len(to_contact_match)} contact_match, "
          f"{len(candidates) - len(to_convert) - len(to_contact_match)} seguem sem elo.")

    used_opps: set[str] = set()
    used_contacts: set[str] = set()
    lead_updates, contact_updates, summary = [], [], []

    def link(lead: dict, pool: list[dict], index: int) -> tuple[dict, date | None, bool]:
        acquired = acquisitions.get(lead["EMAIL"].lower())
        before = acquired is not None and index < N_OPP_BEFORE_ACQUISITION
        free_pool = [o for o in pool if contact_by_opp[o["ID"]] not in used_contacts]
        opp = pick_opportunity(free_pool, used_opps, acquired, before)
        used_opps.add(opp["ID"])
        used_contacts.add(contact_by_opp[opp["ID"]])
        return opp, acquired, before

    # Leads com envio de formulário primeiro, para a sujeira "antes da aquisição" cair num Lead de jornada
    def journey_first(group):
        return sorted(group, key=lambda l: l["EMAIL"].lower() not in acquisitions)

    for i, lead in enumerate(journey_first(to_convert)):
        opp, acquired, before = link(lead, opps_with_role, i)
        converted_on = opp_created(opp)
        if before:
            # converteu numa Opportunity que já estava aberta: a conversão é posterior à aquisição
            converted_on = acquired + timedelta(days=random.randint(3, 20))
        lead_updates.append({
            "ID": lead["ID"],
            "ISCONVERTED": "true",
            "CONVERTEDDATE": converted_on.isoformat(),
            "CONVERTEDACCOUNTID": opp["ACCOUNTID"],
            "CONVERTEDCONTACTID": contact_by_opp[opp["ID"]],
            "CONVERTEDOPPORTUNITYID": opp["ID"],
            "SYSTEMMODSTAMP": SYNC_AT,
        })
        summary.append(("converted", lead, opp, acquired, before))

    for i, lead in enumerate(journey_first(to_contact_match)):
        opp, acquired, before = link(lead, opps_single_contact, i)
        email = lead["EMAIL"]
        if random.random() < RATE_CONTACT_EMAIL_DIRTY:
            email = dirty_email(email)
        contact_updates.append({
            "ID": contact_by_opp[opp["ID"]],
            "EMAIL": email,
            "SYSTEMMODSTAMP": SYNC_AT,
        })
        summary.append(("contact_match", lead, opp, acquired, before))

    lead_updates.sort(key=lambda r: r["ID"])
    contact_updates.sort(key=lambda r: r["ID"])
    write_csv("salesforce_lead_conversions.csv", lead_updates,
              ["ID", "ISCONVERTED", "CONVERTEDDATE", "CONVERTEDACCOUNTID", "CONVERTEDCONTACTID",
               "CONVERTEDOPPORTUNITYID", "SYSTEMMODSTAMP"])
    write_csv("salesforce_contact_email_updates.csv", contact_updates, ["ID", "EMAIL", "SYSTEMMODSTAMP"])

    for path in ("converted", "contact_match"):
        rows = [s for s in summary if s[0] == path]
        journey = sum(1 for s in rows if s[3] is not None)
        won = [s[2] for s in rows if s[2]["ISWON"]]
        print(f"{path}: {len(rows)} Leads ({journey} com jornada), {sum(1 for s in rows if s[4])} com "
              f"Opportunity anterior à aquisição, {len(won)} ganhas (amount {sum(o['AMOUNT'] or 0 for o in won):,.2f})")
    dirty = sum(1 for u in contact_updates if u["EMAIL"] != u["EMAIL"].lower())
    print(f"Contacts com e-mail em caixa diferente: {dirty}")
    print("Concluído.")


def write_csv(filename: str, rows: list[dict], fields: list[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Gravado: {path} ({len(rows)} linhas)")


if __name__ == "__main__":
    main()
