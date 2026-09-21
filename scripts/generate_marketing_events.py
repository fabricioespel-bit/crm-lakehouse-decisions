import random 
import uuid 
import csv 

from datetime import datetime, timedelta
from faker import Faker
from generate_sample_data import sf
from pathlib import Path

faker = Faker("pt_BR")
random.seed(42)

# --- Volumes (ver PLANO.md seção 2/7) ---
N_CAMPAIGNS = 8
CLICKS_PER_CAMPAIGN = (150, 400)
CTR_RANGE = (0.01, 0.03) # impressoes calculadas a partir do numero de cliques

# --- Canais: cada um define utm_source/utm_medium 
CHANNELS = [
    {"utm_source": "google", "utm_medium": "cpc"},
    {"utm_source": "meta", "utm_medium": "paid_social"},
    {"utm_source": "linkedin", "utm_medium": "paid_social"},
    {"utm_source": "newsletter", "utm_medium": "email"},
]

CAMPAIGN_THEMES = [
    "promo_verao", "lancamento_produto", "webinar_gestao", "case_cliente",
    "black_friday", "trial_gratuito", "demo_agendada", "conteudo_educativo",
]

def generate_campaigns(n: int) -> list[dict]:
    campaigns = []
    for i in range(n):
        channel = random.choice(CHANNELS)
        campaigns.append({
            "campaign_id": str(uuid.uuid4()),
            "utm_source": channel["utm_source"],
            "utm_medium": channel["utm_medium"],
            "utm_campaign": CAMPAIGN_THEMES[i % len(CAMPAIGN_THEMES)],
        })
    return campaigns

def generate_click_events(campaigns: list[dict]) -> list[dict]:
    events = []
    for campaign in campaigns:
        n_clicks = random.randint(*CLICKS_PER_CAMPAIGN)
        for _ in range(n_clicks):
            events.append({
                "click_id": str(uuid.uuid4()),
                "campaign_id": campaign["campaign_id"],
                "utm_source": campaign["utm_source"],
                "utm_medium": campaign["utm_medium"],
                "utm_campaign": campaign["utm_campaign"],
                "event_timestamp": faker.date_time_between(start_date="-18M", end_date="-1M").isoformat(),
            })
    return events

# Custo por clique (CPC) varia por canal — pago de verdade (Google/Meta/LinkedIn) tem custo,
# e-mail marketing (canal próprio) não tem custo por clique, só custo fixo de ferramenta
# (fora de escopo aqui, tratamos como zero)
CPC_RANGES = {
    "google": (2.50, 6.00),
    "meta": (1.20, 3.50),
    "linkedin": (5.00, 12.00),
    "newsletter": (0.0, 0.0),
}

def generate_campaign_stats(campaigns: list[dict], click_events: list[dict]) -> list[dict]:
    clicks_by_campaign: dict[str, int] = {}
    for event in click_events:
        clicks_by_campaign[event["campaign_id"]] = clicks_by_campaign.get(event["campaign_id"], 0) + 1

    stats = []
    for campaign in campaigns:
        n_clicks = clicks_by_campaign.get(campaign["campaign_id"], 0)
        ctr = random.uniform(*CTR_RANGE)
        impressions = round(n_clicks / ctr) if ctr > 0 else 0

        cpc_range = CPC_RANGES[campaign["utm_source"]]
        avg_cpc = random.uniform(*cpc_range)
        cost = round(n_clicks * avg_cpc, 2)

        stats.append({
            "campaign_id": campaign["campaign_id"],
            "impressions": impressions,
            "clicks": n_clicks,
            "cost": cost,
        })
    return stats

ATTRIBUTION_RATE = 0.70   # fração dos Leads existentes que "vieram" de marketing
PROPAGATION_RATE = 0.65   # já decidido — fração que retém os UTMs de volta no Salesforce


def fetch_existing_leads() -> list[dict]:
    result = sf.query("SELECT Id, CreatedDate FROM Lead")
    return result["records"]


def assign_leads_to_clicks(leads: list[dict], click_events: list[dict]) -> list[dict]:
    """Escolhe uma fração dos Leads como vindos de marketing, e associa cada um a um
    clique com timestamp anterior à criação do Lead. Retorna só os Leads escolhidos com
    sucesso, cada um com o clique correspondente embutido em 'matched_click'."""
    n_attributed = round(len(leads) * ATTRIBUTION_RATE)
    chosen_leads = random.sample(leads, k=n_attributed)

    assignments = []
    for lead in chosen_leads:
        lead_created = datetime.fromisoformat(
            lead["CreatedDate"].replace("Z", "+00:00")
        ).replace(tzinfo=None)

        candidates = [
            e for e in click_events
            if datetime.fromisoformat(e["event_timestamp"]) < lead_created
        ]
        if not candidates:
            continue

        assignments.append({
            "lead_id": lead["Id"],
            "matched_click": random.choice(candidates),
        })

    return assignments

def update_leads_with_utm(assignments: list[dict]) -> int:
    """Grava os campos UTM de volta no Salesforce, só pra uma fração dos Leads atribuídos
    (simulando a perda de rastreamento). Retorna quantos Leads foram atualizados."""
    to_update = []
    for assignment in assignments:
        if random.random() < PROPAGATION_RATE:
            click = assignment["matched_click"]
            to_update.append({
                "Id": assignment["lead_id"],
                "UTM_Source__c": click["utm_source"],
                "UTM_Medium__c": click["utm_medium"],
                "UTM_Campaign__c": click["utm_campaign"],
            })

    if to_update:
        results = sf.bulk.Lead.update(to_update)
        failed = [r for r in results if not r["success"]]
    if failed:
        raise RuntimeError(f"{len(failed)} updates de Lead falharam: {failed[:3]}")

    return len(to_update)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def write_csv(filename: str, rows: list[dict]) -> None:
    if not rows:
        return
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Gravado: {path} ({len(rows)} linhas)")


def main():
    print("Gerando campanhas e eventos de clique...")
    campaigns = generate_campaigns(N_CAMPAIGNS)
    click_events = generate_click_events(campaigns)
    campaign_stats = generate_campaign_stats(campaigns, click_events)
    print(f"{len(campaigns)} campanhas, {len(click_events)} cliques.")

    write_csv("marketing_campaigns.csv", campaigns)
    write_csv("marketing_click_events.csv", click_events)
    write_csv("marketing_campaign_stats.csv", campaign_stats)

    print("Buscando Leads existentes no Salesforce...")
    leads = fetch_existing_leads()
    assignments = assign_leads_to_clicks(leads, click_events)
    print(f"{len(assignments)} Leads associados a um clique.")

    n_updated = update_leads_with_utm(assignments)
    print(f"{n_updated} Leads atualizados com UTM no Salesforce.")

    print("Concluído.")


if __name__ == "__main__":
    main()