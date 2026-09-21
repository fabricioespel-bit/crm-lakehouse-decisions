import os 
import random 
from datetime import datetime, timedelta 

from dotenv import load_dotenv 
from faker import Faker
from simple_salesforce import Salesforce

load_dotenv()

fake = Faker("pt_BR")
random.seed(42)

# --- Volumes ---
N_ACCOUNTS = 65
CONTACTS_PER_ACCOUNT = (1, 4) # min, max
N_OPPORTUNITIES = 200
N_LEADS = 125

# --- Taxas de "corrupção" proposital (ver PLANO.md seção 4/7)
RATE_DUPLICATE_ACCOUNT = 0.09
RATE_INCONSISTENT_PICKLIST = 0.15
RATE_MISSING_CONTACT_ROLE = 0.20
RATE_MISSING_LEAD_SOURCE = 0.25
RATE_ILLOGICAL_DATES = 0.05

sf = Salesforce(
    username=os.environ["SF_USERNAME"],
    password=os.environ["SF_PASSWORD"],
    security_token=os.environ["SF_SECURITY_TOKEN"],
)

INDUSTRIES = ["Technology", "Healthcare", "Manufacturing", "Retail", "Financial Services", "Education"]

# Variações "sujas" para cada Industry válida - usadas quando a taxa de inconsistência dispara
INDUSTRY_VARIANTS = {
    "Technology": ["Tech", "tech", "Technology"],
    "Healthcare": ["Health Care", "healthecare"],
    "Financial Services": ["Financial", "finance"],
}

def mutant_account_name(name:str) -> str:
    """Gera uma variação 'suja' de um nome de Account existente, simulando
    cadastro duplicado manual (maiusculas, sufixo societário, espaço extra)."""
    variants = [
        name.upper(),
        name + " ",
        f"{name} LTDA",
        name.replace("Ltda", "").strip(),
    ]
    return random.choice(variants)

def generate_accounts(n: int) -> list[dict]:
    accounts = []
    for _ in range(n):
        industry = random.choice(INDUSTRIES)
        if industry in INDUSTRY_VARIANTS and random.random() < RATE_INCONSISTENT_PICKLIST:
            industry = random.choice(INDUSTRY_VARIANTS[industry])
        
        accounts.append({
            "Name": fake.company(),
            "Industry": industry,
            "BillingCity": fake.city(),
            "BillingStateCode": fake.estado_sigla(),
            "BillingCountryCode": "BR",
            "Phone": fake.phone_number(),
            "Website": fake.url(),
            "NumberOfEmployees": random.randint(5,5000),
        })
    
    # Injeta duplicidade: pega Accounts já geradas (nunca uma duplicata de duplicata)
    # e cria uma variação do nome como registro novo e separado.
    n_duplicates = round(n * RATE_DUPLICATE_ACCOUNT)
    originals = random.sample(accounts, k=n_duplicates)
    for original in originals:
        duplicate = original.copy()
        duplicate["Name"] = mutant_account_name(original["Name"])
        accounts.append(duplicate)
        
    return accounts

def insert_accounts(accounts: list[dict]) -> list[str]:
    """Insere contas via API REST do Salesforce.
    Retorna lista de IDs criados"""
    results = sf.bulk.Accounts.insert(accounts)
    failed = [r for r in results if not r["success"]]
    if failed:
        raise RuntimeError(f"{len(failed)} Accounts falharam ao inserir:{failed[:3]}")
    return [r["id"] for r in results]

def generate_contacts(account_ids: list[str]) -> list[dict]:
    contacts = []
    for account_id in account_ids:
        n_contacts = random.randint(*CONTACTS_PER_ACCOUNT)
        for _ in range(n_contacts):
            first_name = fake.first_name()
            last_name = fake.last_name()
            contacts.append({
                "AccountId": account_id,
                "FirstName": first_name,
                "LastName": last_name,
                "Email": fake.unique.email(),
                "Phone": fake.phone_number(),
                "Title": fake.job()
            })
    return contacts
        
LEAD_SOURCES = ["Web", "Phone Inquiry", "Partner Referral", "Trade Show", "Employee Referral"]
LEAD_STATUSES = ["Open - Not Contacted", "Working - Contacted", "Closed - Converted", "Closed - Not Converted"]

def generate_leads(n: int) -> list[dict]:
    leads = []
    for _ in range(n):
        lead_source = random.choice(LEAD_SOURCES)
        if random.random() < RATE_MISSING_LEAD_SOURCE:
            lead_source = random.choice([None, "Other"])

        leads.append({
            "FirstName": fake.first_name(),
            "LastName": fake.last_name(),
            "Company": fake.company(),
            "Email": fake.unique.email(),
            "Phone": fake.phone_number(),
            "LeadSource": lead_source,
            "Status": random.choice(LEAD_STATUSES),
            "Industry": random.choice(INDUSTRIES),
        })
    return leads

STAGE_DISTRIBUTION = {
    "Prospecting": 0.25,
    "Qualification": 0.20,
    "Needs Analysis": 0.15,
    "Proposal/Price Quote": 0.12,
    "Negotiation/Review": 0.08,
    "Closed Won": 0.12,
    "Closed Lost": 0.08,
}

def generate_opportunities(account_ids: list[str], n: int) -> tuple[list[dict], list[bool]]:
    """Retorna (opportunities, precisa_contact_role) — a segunda lista alinhada por índice
    indica quais Opportunities DEVERIAM ganhar um Contact Role (antes de aplicar a taxa de ausência)."""
    stages = list(STAGE_DISTRIBUTION.keys())
    weights = list(STAGE_DISTRIBUTION.values())

    opportunities = []
    needs_contact_role = []
    for _ in range(n):
        stage = random.choices(stages, weights=weights, k=1)[0]
        created_date = fake.date_between(start_date="-18M", end_date="-1M")

        is_closed = stage.startswith("Closed")
        if is_closed:
            close_date = fake.date_between(start_date=created_date, end_date="today")
            if random.random() < RATE_ILLOGICAL_DATES:
                close_date = created_date - timedelta(days=random.randint(1, 30))
        else:
            close_date = created_date + timedelta(days=random.randint(15, 90))

        opportunities.append({
            "AccountId": random.choice(account_ids),
            "Name": f"{fake.bs().capitalize()} - {fake.company()}",
            "StageName": stage,
            "Amount": round(random.uniform(5_000, 250_000), 2),
            "CloseDate": close_date.isoformat(),
            "CreatedDate": created_date.isoformat(),
        })
        needs_contact_role.append(random.random() >= RATE_MISSING_CONTACT_ROLE)

    return opportunities, needs_contact_role

def insert_records(sobject_name: str, records: list[dict]) -> list[str]:
    """Insere registros via Bulk API num sObject qualquer e retorna os IDs criados."""
    bulk_handler = getattr(sf.bulk, sobject_name)
    results = bulk_handler.insert(records)
    failed = [r for r in results if not r["success"]]
    if failed:
        raise RuntimeError(f"{len(failed)} registros de {sobject_name} falharam: {failed[:3]}")
    return [r["id"] for r in results]


def insert_contact_roles(opportunity_ids: list[str], contacts_by_account: dict, opportunities: list[dict], needs_contact_role: list[bool]) -> None:
    """Cria OpportunityContactRole vinculando cada Opportunity a um Contact da mesma Account,
    exceto onde needs_contact_role[i] é False (sujeira proposital)."""
    roles = []
    for opp_id, opp, needs_role in zip(opportunity_ids, opportunities, needs_contact_role):
        if not needs_role:
            continue
        account_contacts = contacts_by_account.get(opp["AccountId"], [])
        if not account_contacts:
            continue
        roles.append({
            "OpportunityId": opp_id,
            "ContactId": random.choice(account_contacts),
            "Role": "Decision Maker",
            "IsPrimary": True,
        })
    if roles:
        insert_records("OpportunityContactRole", roles)

def main():
    print("Gerando e inserindo Accounts...")
    accounts = generate_accounts(N_ACCOUNTS)
    account_ids = insert_records("Account", accounts)
    print(f"{len(account_ids)} Accounts inseridas.")

    print("Gerando e inserindo Contacts...")
    contacts = generate_contacts(account_ids)
    contact_ids = insert_records("Contact", contacts)
    contacts_by_account: dict[str, list[str]] = {}
    for contact, contact_id in zip(contacts, contact_ids):
        contacts_by_account.setdefault(contact["AccountId"], []).append(contact_id)
    print(f"{len(contact_ids)} Contacts inseridos.")

    print("Gerando e inserindo Leads...")
    leads = generate_leads(N_LEADS)
    lead_ids = insert_records("Lead", leads)
    print(f"{len(lead_ids)} Leads inseridos.")

    print("Gerando e inserindo Opportunities...")
    opportunities, needs_contact_role = generate_opportunities(account_ids, N_OPPORTUNITIES)
    opportunity_ids = insert_records("Opportunity", opportunities)
    print(f"{len(opportunity_ids)} Opportunities inseridas.")

    print("Criando OpportunityContactRoles (com sujeira de ausência)...")
    insert_contact_roles(opportunity_ids, contacts_by_account, opportunities, needs_contact_role)
    print("Done.")


if __name__ == "__main__":
    main()
