"""Reproducible English synthetic RFPs, scoring keys and instrument fixtures.

These are generated procurement scenarios, not real tenders or model results.
The 100-project catalogue varies the business problem as well as presentation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import re

GEN_VERSION = "3.0-en"

# Each project has a different operating workflow, not just a different client name.
PROJECTS = {
    "healthcare": [
        ("Hospital bed coordination", "match emergency arrivals to staffed beds", "bed turnover, isolation rules, discharge notifications"),
        ("Regional vaccination booking", "schedule cold-chain vaccination sessions", "dose eligibility, vial allocation, appointment recall"),
        ("Pathology specimen tracking", "trace tissue samples between laboratories", "barcode custody, staining batches, result sign-off"),
        ("Home dialysis support", "coordinate supplies for home dialysis patients", "consumable forecasts, delivery exceptions, clinical escalation"),
        ("Community mental-health referrals", "route referrals to appropriate care teams", "triage consent, waiting-list prioritisation, safeguarding handovers")],
    "transport": [
        ("Bus depot charging", "allocate electric buses to charging bays", "battery state, route departure windows, transformer capacity"),
        ("Rail possession planning", "schedule track maintenance without conflicting movements", "worksite permits, isolation boundaries, train-path conflicts"),
        ("Accessible demand-responsive travel", "dispatch wheelchair-accessible shared rides", "lift capacity, escort allocation, pickup commitments"),
        ("Ferry berth allocation", "coordinate vessel arrivals at island terminals", "tidal restrictions, berth occupancy, vehicle loading"),
        ("School-route assurance", "verify contracted student transport services", "stop attendance, guardian authorisation, route substitutions")],
    "energy": [
        ("District heat balancing", "balance supply across a municipal heat network", "heat-meter readings, return temperatures, plant dispatch"),
        ("Community solar settlement", "allocate shared solar generation to members", "interval production, ownership changes, credit settlement"),
        ("Wind maintenance permits", "control turbine maintenance work authorisations", "weather limits, technician certification, lockout evidence"),
        ("Grid connection applications", "assess requests to connect distributed generation", "feeder constraints, study queues, capacity reservations"),
        ("Public building energy retrofit", "verify savings from building retrofits", "weather-normalised baselines, occupancy adjustment, savings guarantees")],
    "water": [
        ("Leak response dispatch", "prioritise reported water leaks for field crews", "pressure zones, excavation permits, repair verification"),
        ("Drinking-water sampling", "schedule statutory drinking-water sampling", "sampling points, laboratory turnaround, exceedance notices"),
        ("Flood-gate operations", "coordinate flood barriers during storm events", "water levels, gate interlocks, emergency overrides"),
        ("Irrigation entitlement trading", "record seasonal irrigation-right transfers", "allocation caps, transfer approvals, metered abstraction"),
        ("Wastewater discharge permits", "manage industrial discharge obligations", "pollutant limits, inspection evidence, enforcement milestones")],
    "education": [
        ("Apprenticeship placement", "match apprentices with approved employers", "competency plans, mentor availability, placement reviews"),
        ("Special-education provision", "coordinate individual support plans", "assessment consent, specialist hours, review meetings"),
        ("University research equipment", "allocate shared scientific instruments", "operator training, calibration windows, recharge approvals"),
        ("Adult language assessment", "organise language-course placement tests", "test accommodations, assessor allocation, level appeals"),
        ("School meal subscriptions", "manage subsidised student meals", "allergen declarations, subsidy eligibility, kitchen forecasts")],
    "housing": [
        ("Emergency shelter intake", "assign temporary shelter places", "household composition, safety restrictions, move-on referrals"),
        ("Housing repairs triage", "prioritise tenant-reported repairs", "hazard classification, contractor appointments, completion inspections"),
        ("Shared-ownership staircasing", "administer additional property-share purchases", "valuation expiry, affordability checks, legal completion"),
        ("Building safety evidence", "maintain evidence for high-rise safety cases", "inspection findings, accountable owners, remediation dependencies"),
        ("Rental deposit mediation", "resolve disputes over rental deposits", "evidence submission, response deadlines, adjudication outcomes")],
    "justice": [
        ("Court interpreter booking", "assign accredited interpreters to hearings", "language pairs, conflicts of interest, remote attendance"),
        ("Legal aid eligibility", "assess applications for funded representation", "income evidence, case categories, eligibility appeals"),
        ("Probation appointment planning", "coordinate supervision appointments", "reporting conditions, officer caseloads, missed-contact escalation"),
        ("Digital evidence disclosure", "manage controlled disclosure of case evidence", "redaction review, disclosure schedules, recipient acknowledgements"),
        ("Restorative justice referrals", "route suitable cases to mediation", "participant consent, facilitator capacity, agreement follow-up")],
    "agriculture": [
        ("Livestock movement certification", "authorise livestock transfers", "holding identifiers, disease restrictions, transport documentation"),
        ("Crop disease surveillance", "triage crop-health observations", "geospatial reports, sample confirmation, outbreak notifications"),
        ("Farm grant inspections", "schedule evidence-based grant inspections", "claim milestones, parcel checks, payment holds"),
        ("Seed lot certification", "trace seed lots through quality certification", "germination tests, lot segregation, certificate withdrawal"),
        ("Organic producer audits", "coordinate organic certification audits", "input records, nonconformities, certification decisions")],
    "culture": [
        ("Museum object loans", "manage temporary loans of collection objects", "condition reports, courier approval, insurance periods"),
        ("Performing arts residencies", "allocate public rehearsal and residency spaces", "technical riders, rehearsal slots, access agreements"),
        ("Oral history archive", "preserve community oral-history recordings", "speaker consent, transcription review, embargo expiry"),
        ("Heritage conservation grants", "administer conservation project awards", "listed-building consent, staged claims, conservation evidence"),
        ("Film location permits", "coordinate filming in public locations", "road closures, resident notices, location deposits")],
    "waste": [
        ("Hazardous waste manifests", "trace hazardous loads to licensed treatment", "waste codes, carrier credentials, treatment confirmations"),
        ("Reuse centre inventory", "redistribute recovered household goods", "safety checks, item reservations, collection appointments"),
        ("Food waste collection", "plan commercial food-waste rounds", "container weights, contamination reports, wash schedules"),
        ("Landfill aftercare monitoring", "monitor closed landfill obligations", "gas readings, groundwater samples, corrective actions"),
        ("Construction material exchange", "match surplus construction materials with demand", "material grading, collection logistics, reuse certificates")],
    "public_safety": [
        ("Wildfire resource staging", "position shared firefighting resources", "crew readiness, equipment availability, incident handovers"),
        ("Civil warning subscriptions", "deliver location-aware emergency warnings", "alert polygons, multilingual messages, delivery receipts"),
        ("Fire inspection scheduling", "prioritise premises for fire-safety inspection", "risk assessments, visit evidence, enforcement follow-up"),
        ("Emergency volunteer mobilisation", "activate vetted emergency volunteers", "skills verification, duty availability, deployment welfare"),
        ("Public-event safety permits", "assess temporary public-event safety plans", "crowd capacity, evacuation routes, multi-agency approvals")],
    "social_care": [
        ("Home-care rostering", "assign qualified carers to home visits", "care continuity, travel time, missed-visit escalation"),
        ("Foster placement matching", "identify suitable foster placements", "sibling groups, carer approvals, placement stability"),
        ("Disability equipment loans", "manage community assistive-equipment loans", "clinical assessment, decontamination, maintenance recalls"),
        ("Unpaid carer respite", "coordinate respite support for unpaid carers", "support entitlements, provider capacity, emergency cover"),
        ("Adult safeguarding referrals", "coordinate safeguarding concerns", "consent capacity, multi-agency actions, protection-plan reviews")],
    "commerce": [
        ("Street market licences", "allocate licensed trading pitches", "trading categories, pitch dimensions, licence renewals"),
        ("Export advice vouchers", "administer funded export advisory support", "business eligibility, adviser accreditation, evidence of delivery"),
        ("Food premises registration", "register and classify food businesses", "operator declarations, premises changes, inspection triggers"),
        ("Local supplier marketplace", "publish small public purchasing opportunities", "supplier verification, quotation windows, award notices"),
        ("Consumer complaint mediation", "route consumer disputes to mediators", "trader responses, evidence exchange, settlement acceptance")],
    "science": [
        ("Biobank sample access", "govern research access to stored biological samples", "ethics approval, sample reservations, material-transfer agreements"),
        ("Telescope observation scheduling", "allocate observatory time to research proposals", "target visibility, instrument changes, weather contingencies"),
        ("Environmental sensor calibration", "coordinate calibration of field sensors", "reference standards, drift thresholds, calibration certificates"),
        ("Clinical trial recruitment", "coordinate consented recruitment for research trials", "protocol eligibility, participant withdrawal, screening logs"),
        ("Research data stewardship", "manage publication of reusable research datasets", "data-management plans, disclosure review, persistent identifiers")],
    "ports": [
        ("Harbour pilot assignment", "allocate licensed pilots to vessel movements", "draft limits, pilot endorsements, transfer-boat availability"),
        ("Container examination bookings", "schedule controlled container examinations", "inspection orders, reefer requirements, release authorisation"),
        ("Shore power reservations", "reserve quayside electrical connections", "connector compatibility, load limits, energy settlement"),
        ("Dredging consent tracking", "coordinate maintenance-dredging approvals", "sediment analysis, disposal sites, ecological windows"),
        ("Marina visitor moorings", "allocate short-stay visitor moorings", "vessel dimensions, berth access, occupancy changes")],
    "finance": [
        ("Municipal bond obligations", "track municipal debt covenants", "payment calendars, covenant ratios, disclosure approvals"),
        ("Supplier invoice matching", "resolve mismatches in payable invoices", "purchase orders, goods receipts, dispute ownership"),
        ("Participatory budgeting", "administer resident-proposed spending projects", "proposal eligibility, voting rules, delivery milestones"),
        ("Travel expense claims", "validate public employee expense claims", "policy limits, exchange rates, approval delegations"),
        ("Small charity grant payments", "release staged charity grant payments", "bank verification, milestone evidence, recovery actions")],
    "planning": [
        ("Tree protection consents", "assess work affecting protected trees", "arborist evidence, consent conditions, replacement planting"),
        ("Building control inspections", "schedule construction-stage compliance inspections", "inspection milestones, structural certificates, completion notices"),
        ("Public consultation submissions", "manage representations on planning proposals", "submission windows, redaction choices, response themes"),
        ("Developer contribution obligations", "track contributions secured through development agreements", "trigger events, indexed amounts, infrastructure delivery"),
        ("Brownfield land remediation", "coordinate contaminated-site remediation evidence", "sampling plans, remediation targets, verification reports")],
    "tourism": [
        ("Accessible visitor itineraries", "publish verified accessible travel itineraries", "access measurements, seasonal closures, visitor feedback"),
        ("Short-stay accommodation register", "register licensed visitor accommodation", "occupancy limits, host verification, licence expiry"),
        ("Protected trail permits", "allocate permits for sensitive hiking routes", "daily quotas, guide credentials, weather closures"),
        ("Tourism levy reconciliation", "reconcile visitor levies declared by accommodation operators", "exempt stays, occupancy declarations, payment adjustments"),
        ("Destination event calendar", "coordinate visitor-facing events across districts", "venue availability, promotion rights, cancellation updates")],
    "sport": [
        ("Swimming lesson allocation", "assign learners to suitable swimming classes", "skill assessment, instructor ratios, waiting-list offers"),
        ("Community pitch booking", "allocate outdoor sports pitches fairly", "club priorities, weather cancellations, maintenance closures"),
        ("Athlete travel support", "administer travel assistance for regional athletes", "event eligibility, approved costs, participation evidence"),
        ("Anti-doping sample logistics", "trace controlled anti-doping sample shipments", "custody seals, courier handovers, laboratory receipts"),
        ("Adaptive sports equipment", "allocate specialist equipment for adaptive sports", "athlete fitting, safety checks, equipment transport")],
    "libraries": [
        ("Mobile library routing", "plan mobile-library visits to underserved settlements", "vehicle access, loan demand, stop frequency"),
        ("Digital lending licences", "allocate licensed digital-library access", "concurrent seats, licence expiry, reservation queues"),
        ("Local studies digitisation", "coordinate digitisation of local-history collections", "rights clearance, image capture, metadata review"),
        ("Library room access", "manage after-hours use of library rooms", "identity checks, access windows, incident reporting"),
        ("Interlibrary loan fulfilment", "coordinate loans between independent library networks", "lending restrictions, dispatch tracking, replacement liability")],
}
DOMAINS = PROJECTS
PERSONAS = {
    "formal_tender": ("Procurement notice", "Mandatory provisions", "Technical schedules"),
    "outcome_brief": ("Outcome-led brief", "What success means", "Delivery commitments"),
    "engineering_spec": ("Engineering specification", "System interfaces", "Verification matrix"),
    "service_charter": ("Service design charter", "User journeys", "Operational promises"),
    "legal_schedule": ("Contract schedules", "Articles of performance", "Annex obligations"),
    "product_backlog": ("Product backlog procurement", "Epics and acceptance", "Release constraints"),
    "questionnaire": ("Supplier response questionnaire", "Questions to bidders", "Response evidence"),
    "decision_memo": ("Investment decision memorandum", "Decisions requested", "Supporting conditions"),
    "work_order": ("Work package request", "Work instructions", "Completion evidence"),
    "operations_manual": ("Operations transition request", "Runbook requirements", "Service handover"),
    "table_matrix": ("Compliance matrix", "Requirement register", "Traceability schedule"),
    "risk_dossier": ("Delivery risk dossier", "Risk-bearing obligations", "Assurance evidence"),
    "dialogue_record": ("Competitive dialogue record", "Agreed discussion points", "Unresolved commitments"),
    "milestone_plan": ("Milestone-based procurement", "Delivery checkpoints", "Entry and exit conditions"),
    "interface_contract": ("Integration contract", "Boundary agreements", "Payload and timing rules"),
    "assurance_case": ("Assurance-led invitation", "Claims requiring evidence", "Evidence obligations"),
    "field_notes": ("Field-service commissioning brief", "Observations from operations", "Required interventions"),
    "board_paper": ("Board approval paper", "Approval conditions", "Investment safeguards"),
    "user_stories": ("User-story tender", "Service stories", "Definition of done"),
    "migration_playbook": ("Migration playbook request", "Transition activities", "Cutover obligations"),
}

# Contradictions contain two independently anchored clauses; the other entries
# deliberately leave an acceptance condition, scope boundary or evidence gap open.
ISSUES = [
    ("contradiction", "availability", ["availability", "outage"], [
        ("Availability shall be at least {uptime}% in every calendar month.", "A scheduled outage of {hours} hours each week is excluded from availability without reducing the stated target."),
        ("The service target includes all maintenance in a {uptime}% monthly availability measure.", "Operations may take the service offline for {hours} hours weekly; those outages do not count."),
        ("Bidders must price {uptime}% monthly availability, including planned work.", "The operating schedule reserves {hours} hours of downtime every week outside the service calculation.")]),
    ("contradiction", "retention", ["retention", "delete"], [
        ("Delete all identifiable service records after {months} months.", "Keep the same identifiable records online for seven years without deletion exceptions."),
        ("Identifiable case data has a mandatory {months}-month retention limit.", "The audit schedule requires seven years of immediately retrievable identifiable case data."),
        ("Erase personal case histories at the end of month {months}.", "Retain every personal case history for seven years; anonymisation is not permitted.")]),
    ("contradiction", "deadline", ["deadline", "rollout"], [
        ("Complete rollout within {weeks} weeks of contract signature.", "The earliest approved access to the required source systems is week {later}, after the rollout deadline."),
        ("The binding rollout deadline is contract week {weeks}.", "Security clearance prevents any source-system access until week {later}."),
        ("All sites must be live by week {weeks}.", "The mandatory discovery phase cannot start until the source owner grants access in week {later}.")]),
    ("contradiction", "residency", ["residency", "region"], [
        ("Every backup must remain within the contracting region.", "Disaster recovery requires an unencrypted backup replica in an overseas region."),
        ("Data residency rules cover primary storage and all backup copies.", "The resilience annex specifies overseas backup replication with no residency exemption."),
        ("No service data may cross the regional boundary, even during recovery.", "The recovery design shall transfer full case databases to a foreign region.")]),
    ("contradiction", "authentication", ["authentication", "offline"], [
        ("Every sign-in requires a live request to the central authentication service.", "Field users must sign in and create records while completely offline."),
        ("Authentication is valid only after an online central check for each login.", "The field acceptance test requires first-time login with no network connection."),
        ("Offline credential caching is prohibited for authentication.", "Mobile teams must authenticate new users at disconnected locations.")]),
    ("contradiction", "ownership", ["ownership", "source"], [
        ("The buyer receives ownership of all bespoke source code.", "The supplier retains exclusive ownership of every delivered source component, including bespoke work."),
        ("Bespoke source ownership transfers to the authority on acceptance.", "The intellectual-property schedule grants the authority no rights in custom source."),
        ("Custom source deliverables become buyer property.", "The licence annex says ownership of custom source never leaves the vendor.")]),
    ("ambiguity", "performance", ["performance", "latency"], [
        ("Performance must be excellent at peak demand; no latency percentile or test load is specified.",),
        ("The service shall feel instantaneous to users; the performance workload and latency threshold remain unstated.",),
        ("Guarantee fast response under realistic usage, without defining concurrency or a performance acceptance boundary.",)]),
    ("ambiguity", "migration_volume", ["volume", "migration"], [
        ("Price the migration of all historical records; the authority supplies no inventory, volume or size estimate.",),
        ("Migration must include the full archive, whose record count and attachment volume have not been measured.",),
        ("Provide a fixed migration price for an unspecified data volume spanning all historical systems.",)]),
    ("ambiguity", "support", ["support", "hours"], [
        ("Provide extended support hours whenever required; coverage days and escalation response times are undefined.",),
        ("The authority expects premium support but has not defined operating hours or severity levels.",),
        ("Include suitable out-of-hours support without a published calendar or response commitment.",)]),
    ("ambiguity", "acceptance", ["acceptance", "approve"], [
        ("Acceptance occurs when stakeholders are satisfied; neither the approver nor the acceptance test is named.",),
        ("All parties must approve readiness, but the contract contains no acceptance authority or pass criteria.",),
        ("Payment depends on successful acceptance with no objective procedure for approving deliverables.",)]),
    ("ambiguity", "indexation", ["indexation", "inflation"], [
        ("Annual charges will follow a fair inflation adjustment; no indexation formula or reference date is provided.",),
        ("Indexation applies on renewal, but the index, base month and cap are still to be agreed.",),
        ("The price schedule permits reasonable inflation uplifts without an indexation method.",)]),
    ("ambiguity", "accessibility_scope", ["accessibility", "scope"], [
        ("Meet accessibility needs on every channel; the scope of kiosk and assisted-service adaptations is not defined.",),
        ("Accessibility applies beyond the web interface, but no in-scope non-web channels are listed.",),
        ("Quote inclusive accessibility for all service touchpoints without an inventory of physical interfaces.",)]),
    ("hidden_requirement", "printed_notices", ["print", "notice"], [
        ("A footnote to invoicing requires suppliers to print and post statutory notices to residents each month.",),
        ("The payment appendix quietly assigns monthly printed notice production and postal fulfilment to the delivery partner.",),
        ("Within the billing notes, the contractor must operate a physical print-and-post notice service.",)]),
    ("hidden_requirement", "training", ["training", "night"], [
        ("The staffing annex requires night-shift training at every operating site, included in the fixed fee.",),
        ("A roster footnote obliges the supplier to deliver onsite training for night crews without additional charges.",),
        ("All night workers must receive instructor-led training at their own site, as stated only in the rota annex.",)]),
    ("hidden_requirement", "hardware", ["hardware", "device"], [
        ("The site appendix makes the supplier responsible for replacing all unsupported user devices within the quoted price.",),
        ("Include hardware refresh for every obsolete endpoint, an obligation appearing only in the facilities schedule.",),
        ("A facilities note requires new device supply, installation and disposal of legacy hardware at supplier cost.",)]),
    ("hidden_requirement", "translation", ["translation", "language"], [
        ("The communications appendix requires certified translation of historic free-text records into three languages.",),
        ("Bidders must translate archived case narratives, including certified language review, under the communications schedule.",),
        ("The language annex assigns certified translation of the entire narrative archive to the successful supplier.",)]),
    ("hidden_requirement", "reconciliation", ["reconciliation", "manual"], [
        ("The finance annex requires manual reconciliation of unmatched historic transactions before final payment.",),
        ("Final payment includes manual reconciliation of every unresolved ledger exception listed in the accounts appendix.",),
        ("The accounts schedule adds supplier-led manual reconciliation for inherited unmatched transactions.",)]),
    ("hidden_requirement", "on_call", ["on-call", "staff"], [
        ("A personnel footnote requires named on-call staff throughout every holiday period at no extra cost.",),
        ("The holiday rota schedule mandates supplier-staffed on-call cover, although the main scope describes software only.",),
        ("Include holiday on-call staffing under the personnel schedule, with no separate rate or service boundary.",)]),
    ("brownfield_signal", "batch_dependency", ["batch", "dependency"], [
        ("Downstream statutory reporting still consumes the existing nightly fixed-width batch export.",),
        ("An external regulator accepts only the incumbent nightly batch file, which remains a live dependency.",),
        ("The nightly reporting batch has an unchanged external consumer that cannot migrate during this contract.",)]),
    ("brownfield_signal", "parallel_running", ["parallel", "legacy"], [
        ("The legacy service must run in parallel with its replacement for two complete reporting cycles.",),
        ("Operate legacy and replacement services concurrently until two reporting periods reconcile.",),
        ("A mandatory parallel-running period spans two complete cycles of the incumbent service.",)]),
    ("brownfield_signal", "calculation_parity", ["rounding", "calculation"], [
        ("The replacement calculation must reproduce every legacy rounding decision, including undocumented historical exceptions.",),
        ("Financial acceptance requires exact calculation parity with incumbent rounding and historical adjustments.",),
        ("Preserve all existing calculation outputs, including undocumented rounding edge cases.",)]),
    ("risk", "supplier_exit", ["exit", "escrow"], [
        ("The contract offers no exit assistance, source escrow or usable data-export commitment if the supplier fails.",),
        ("No supplier-exit procedure, escrow agreement or independently usable export is included.",),
        ("Supplier insolvency has no defined exit plan or escrow mechanism, despite exclusive hosting.",)]),
    ("risk", "manual_override", ["override", "audit"], [
        ("Operators can override eligibility decisions without recording who changed the decision or why.",),
        ("Privileged override actions bypass the audit trail and require no recorded justification.",),
        ("Manual decision override is unrestricted and produces no attributable audit event.",)]),
    ("risk", "backup_restore", ["restore", "backup"], [
        ("Backups are copied daily, but the contract requires no restore test or recovery evidence.",),
        ("The backup policy contains no scheduled restore rehearsal, despite daily copy jobs.",),
        ("A successful backup job is treated as proof of recoverability without any restore verification.",)]),
    ("risk", "shared_identity", ["shared", "account"], [
        ("All temporary operators will use a shared administrator account during peak periods.",),
        ("Peak staffing is handled through one shared privileged account with no individual attribution.",),
        ("The operating plan distributes a common admin password to temporary teams.",)]),
    ("scope_overlap", "adjacent_platform", ["adjacent", "scope"], [
        ("The adjacent analytics platform is excluded from scope, yet the supplier must redesign its data model and screens.",),
        ("Analytics ownership stays outside the contract while the same adjacent platform requires a complete supplier rebuild.",),
        ("The scope excludes the reporting portal but still assigns its schema and interface redesign to the contractor.",)]),
    ("scope_overlap", "identity_rebuild", ["identity", "scope"], [
        ("Identity infrastructure is outside scope, but the supplier must replace the enterprise directory as part of delivery.",),
        ("The shared identity directory is retained and excluded, while the integration schedule orders its full replacement.",),
        ("Enterprise identity is a client-managed dependency, yet directory migration is priced as a supplier deliverable.",)]),
    ("legacy_unknown", "source_access", ["source", "unknown"], [
        ("Commit to a fixed replacement price before source code, schemas or representative data can be inspected.",),
        ("No source or schema access is available before award, although bidders must guarantee complete functional parity.",),
        ("Guarantee the migration scope while legacy source, database structure and sample records remain unavailable.",)]),
    ("legacy_unknown", "integration_inventory", ["integration", "inventory"], [
        ("The integration inventory is incomplete and the incumbent owner cannot identify every active consumer.",),
        ("Guarantee compatibility with all integrations even though no complete interface inventory exists.",),
        ("Active interface consumers are unknown; the authority has no verified integration catalogue.",)]),
    ("legacy_unknown", "data_quality", ["data quality", "profiling"], [
        ("No data-quality profiling has been conducted, yet the price assumes every historic record can be migrated unchanged.",),
        ("Historic data quality is unknown and no profiling sample will be provided before fixed-price award.",),
        ("The buyer assumes clean source data without profiling, duplicate analysis or representative quality evidence.",)]),
]

STYLES = list(PERSONAS)
STACKS = ["Java and PostgreSQL", ".NET and SQL Server", "Python and PostgreSQL",
          "COBOL and DB2", "PHP and MariaDB", "JavaScript and document storage",
          "vendor SaaS with CSV exports", "desktop clients and an embedded database"]

PHRASING = [
    (r"\bthe supplier\b", ["the supplier", "the contractor", "the delivery partner", "the appointed provider"]),
    (r"\bthe authority\b", ["the authority", "the buyer", "the commissioning body", "the procuring organisation"]),
    (r"\bthe contract\b", ["the contract", "the agreement", "the procurement terms", "the delivery agreement"]),
    (r"\bthe service\b", ["the service", "the proposed solution", "the commissioned platform", "the operational system"]),
    (r"\bbefore\b", ["before", "prior to", "in advance of"]),
    (r"\bafter\b", ["after", "following", "subsequent to"]),
    (r"\bwithout\b", ["without", "in the absence of"]),
    (r"\bincluding\b", ["including", "covering", "encompassing"]),
    (r"\bmust\b", ["must", "shall"]),
    (r"\bshall\b", ["shall", "must"]),
    (r"\bevery\b", ["every", "each", "each individual"]),
    (r"\ball\b", ["all", "the full set of", "the complete set of"]),
    (r"\bis not\b", ["is not", "is explicitly not", "is never"]),
    (r"\bprovided\b", ["provided", "supplied", "made available"]),
    (r"\brequires\b", ["requires", "mandates", "calls for", "stipulates"]),
    (r"\bmandatory\b", ["mandatory", "compulsory", "non-optional"]),
    (r"\bexisting\b", ["existing", "current", "incumbent"]),
    (r"\badditional\b", ["additional", "extra", "supplementary"]),
    (r"\bunspecified\b", ["unspecified", "undefined", "undetermined"]),
    (r"\brepresentative\b", ["representative", "realistic", "operationally meaningful"]),
    (r"\bcomplete\b", ["complete", "comprehensive", "exhaustive"]),
    (r"\bapplicable\b", ["applicable", "relevant", "in-scope"]),
    (r"\bseparate\b", ["separate", "distinct", "dedicated"]),
    (r"\bonly\b", ["only", "exclusively", "solely"]),
    (r"\bquoted price\b", ["quoted price", "tendered amount", "offered fixed fee"]),
    (r"\bworking\b", ["working", "operational", "functioning"]),
    (r"\bimmediately\b", ["immediately", "instantly", "without delay"]),
    (r"\brecorded\b", ["recorded", "documented", "logged"]),
    (r"\bincluded\b", ["included", "incorporated", "covered"]),
    (r"\bretrievable\b", ["retrievable", "accessible", "recoverable"]),
    (r"\bpersonal case\b", ["personal case", "identifiable service case", "individual client case"]),
    (r"\bthe buyer\b", ["the buyer", "the purchasing body", "the commissioning organisation"]),
    (r"\bhas not\b", ["has not", "has never", "has still not"]),
    (r"\bthe same\b", ["the same", "those exact", "the identical"]),
    (r"\bno extra cost\b", ["no extra cost", "no supplementary charge", "no increase in the agreed fee"]),
]


def edit_text(text: str, rng: random.Random) -> str:
    """Vary procurement phrasing without changing quantities or planted obligations."""
    for pattern, alternatives in PHRASING:
        replacement = rng.choice(alternatives)
        def replace(match):
            return replacement[0].upper() + replacement[1:] if match[0][0].isupper() else replacement
        text = re.sub(pattern, replace, text, flags=re.I)
    return text


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_case(seed: int, index: int, domain: str | None = None, role: str = "test",
                  persona: str | None = None, dept_variant: int = 0, attempt: int = 0) -> dict:
    rng = random.Random(f"{GEN_VERSION}|{seed}|{index}|{attempt}")
    domains = list(PROJECTS)
    domain = domain or domains[(max(index, 1) - 1) % len(domains)]
    project_index = ((max(index, 1) - 1) // len(domains)) % 5
    title, goal, workflow = PROJECTS[domain][project_index]
    if role == "calibration":
        title = "Cross-agency infrastructure permit triage"
        goal = "coordinate urgent infrastructure permits across independent agencies"
        workflow = "agency ownership, permit dependencies, emergency decision records"
    persona = persona or STYLES[(index + project_index * 3) % len(STYLES)]
    document_title, body_heading, annex_heading = PERSONAS[persona]
    case_id = f"{index:03d}-{domain}-{sha256_text(f'{seed}|{index}')[:6]}"
    values = dict(uptime=rng.choice([99.9, 99.95, 99.99]), hours=rng.randint(3, 8),
                  months=rng.choice([6, 12, 18]), weeks=rng.randint(6, 12), later=rng.randint(16, 24))
    chosen = rng.sample(range(len(ISSUES)), 15)
    rng.shuffle(chosen)
    paragraphs, annexes, mutants = [], [], []
    count = 0

    def add(text: str, annex: bool = False) -> str:
        nonlocal count
        count += 1
        ref = f"{'A' if annex else 'P'}-{count:02d}"
        (annexes if annex else paragraphs).append((ref, edit_text(text, rng)))
        return ref

    stack = rng.choice(STACKS)
    add(f"Procure a capability to {goal}, currently supported by {stack}.")
    for feature in workflow.split(", "):
        add(rng.choice([
            f"Demonstrate {feature} against operational {title.lower()} scenarios.",
            f"Acceptance evidence: show working {feature} for the {title.lower()} team.",
            f"Provide {feature}; the {title.lower()} service owner approves the demonstration.",
            f"The {title.lower()} work package includes verifiable {feature}.",
            f"Operational users require {feature} as part of {title.lower()}.",
            f"For {title.lower()}, document and test the handling of {feature}.",
            f"Deliver {feature}, with a walkthrough using realistic {title.lower()} records.",
            f"Explain how {feature} will operate throughout the {title.lower()} lifecycle."]))
    add(f"Interface boundary: {workflow.split(', ')[0]}; maintain continuity for {title.lower()}.")
    for number, template_index in enumerate(chosen, 1):
        kind, label, keywords, variants = ISSUES[template_index]
        variant = rng.choice(variants)
        refs = [add(text.format(**values), annex=(part > 0 or (number % 4 == 0)))
                for part, text in enumerate(variant)]
        mutants.append(dict(id=f"M{number:02d}", kind=kind, label=label.replace("_", " "),
                            keywords_any=keywords, refs=sorted(refs), template=label,
                            severity="critical" if kind == "contradiction" else "major"))
    controls = [
        dict(id="C01", label="Accessible digital interfaces", keywords_any=["accessibility", "301 549"],
             ref=add(rng.choice([
                 "Accessibility acceptance: test digital interfaces against EN 301 549 with assistive technologies.",
                 "Provide EN 301 549 accessibility evidence, including screen-reader and keyboard-only testing.",
                 "Digital delivery requires accessibility verification under EN 301 549 prior to sign-off.",
                 "Demonstrate accessibility using EN 301 549 tests and independent assistive-technology checks.",
                 "Acceptance includes EN 301 549 compliance and documented accessibility testing.",
                 "Submit a verified accessibility assessment of every digital channel using EN 301 549."]))),
        dict(id="C02", label="Personal data safeguards", keywords_any=["personal data", "processor"],
             ref=add(rng.choice([
                 "The personal data processor must isolate environments and log individually attributable access.",
                 "Processor duties cover personal data access restrictions, segregated environments and traceable actions.",
                 "Protect personal data through named accounts, separated environments and processor audit records.",
                 "Processing personal data requires individual authorisation, environment separation and operation logging.",
                 "Record processor access to personal data with named identities and separate production from testing.",
                 "The appointed processor shall safeguard personal data with segregation, access control and audit logs."])))]
    decoys = []
    for number, (label, text, keywords) in enumerate([
            ("recovery_target", "Recovery exercises must demonstrate a four-hour restoration target and a one-hour data-loss limit.", ["recovery", "target"]),
            ("open_exports", "The service must export structured records using documented open formats, with an annual portability test.", ["export", "format"]),
            ("release_testing", "Every release must pass regression tests in a separate non-production environment before approval.", ["regression", "environment"])], 1):
        decoys.append(dict(id=f"D{number:02d}", label=f"Valid requirement: {label}", kind="ambiguity",
                           keywords_any=keywords, refs=[add(text, annex=True)]))
    conditions = add(rng.choice([
        "Before fixing the price, list contradictions, assumptions and required evidence. Implementation code is unavailable during bidding.",
        "Bidders must identify conflicting obligations and unresolved assumptions; source inspection is not available before award.",
        "Submit clarification questions and an evidence request before committing to scope. Proposals cannot rely on inspecting code.",
        "State dependencies and outstanding conflicts explicitly. Pricing precedes access to source code and requires declared assumptions.",
        "Disclose unknowns affecting delivery or price; no implementation source is accessible to tender respondents.",
        "The commercial response must expose unresolved assumptions and contradictions. Source-code access starts only after award."]))
    prefix = (f"# {document_title}: {title}\n\n"
              "> **SYNTHETIC EVALUATION INPUT.** Not a real tender. Bracketed P/A identifiers are citation anchors, "
              "not requirement priorities. No scoring key is supplied to the respondent.\n\n"
              f"Buyer: {title} commissioning partnership\nReference: {case_id}\n"
              f"Primary outcome: {goal}.\n\n")
    headings = [body_heading + f" / {title}", annex_heading + f" / {workflow.split(', ')[-1]}"]
    rng.shuffle(paragraphs)

    def render(items: list[tuple[str, str]], heading: str) -> str:
        lines = [f"## {heading}", ""]
        mode = STYLES.index(persona) % 10
        if mode in (0, 5):
            lines += ["| Reference | Contract provision |", "|---|---|"]
            lines += [f"| [{ref}] | {text} |" for ref, text in items]
        else:
            for i, (ref, text) in enumerate(items, 1):
                if mode == 1:
                    line = f"- [{ref}] **Outcome {i}:** {text}"
                elif mode == 2:
                    line = f"[{ref}] SHALL-{i:03d}: {text}"
                elif mode == 3:
                    line = f"[{ref}] Service commitment {i}\n  {text}"
                elif mode == 4:
                    line = f"[{ref}] Article {i}. {text}"
                elif mode == 6:
                    line = f"[{ref}] Q{i}. How will your proposal address this provision?\n> {text}"
                elif mode == 7:
                    line = f"[{ref}] Decision item {i}\n: {text}"
                elif mode == 8:
                    line = f"### Work item {i}: {title.split()[0]}\n[{ref}] {text}"
                else:
                    line = f"{i}. [{ref}] {text}"
                lines += [line, ""]
        return "\n".join(lines) + "\n"

    text = prefix + render(paragraphs, headings[0]) + "\n" + render(annexes, headings[1])
    # Number anchors in final reading order so sequence audits reflect the document.
    counters = {"P": 0, "A": 0}
    renamed = {}
    for old in re.findall(r"\[([PA]-\d{2})\]", text):
        counters[old[0]] += 1
        renamed[old] = f"{old[0]}-{counters[old[0]]:02d}"
    text = re.sub(r"\[([PA]-\d{2})\]", lambda match: f"[{renamed[match[1]]}]", text)
    for entry in mutants + decoys:
        entry["refs"] = sorted(renamed[ref] for ref in entry["refs"])
    for control in controls:
        control["ref"] = renamed[control["ref"]]
    conditions = renamed[conditions]
    ids = sorted(set(re.findall(r"\[([PA]-\d{2})\]", text)))
    key = dict(fixture_id=case_id, generator=dict(version=GEN_VERSION, index=index, role=role),
               mutants=mutants, controls=controls, decoys=decoys,
               covariates=dict(domain=domain, project=title, client=f"{title} commissioning partnership",
                               persona=persona, department=body_heading, register="English",
                               stack=stack, conditions_anchor=conditions, n_anchors=len(ids),
                               n_sections=text.count("\n## "), generation_attempt=attempt))
    return dict(id=case_id, domain=domain, persona=persona, role=role, rfp=text, key=key, source_ids=ids)


def oracle_report(case: dict) -> dict:
    """Construct expected output from the key for offline tests, never LLM evidence."""
    key = case["key"]
    requirements = [dict(description=f"Verify the anchored contractual obligation {ref}",
                         priority="must", verification="Use a documented acceptance test", source_refs=[ref])
                    for ref in case["source_ids"]]
    requirements += [dict(description=c["label"] + " " + " ".join(c["keywords_any"]),
                          priority="must", verification="Record independent compliance evidence",
                          source_refs=[c["ref"]]) for c in key["controls"]]
    return dict(requirements=requirements,
                findings=[dict(kind=m["kind"], summary=m["label"] + ": " + " ".join(m["keywords_any"]),
                               impact="Unresolved contractual exposure affects delivery scope or price.",
                               recommendation="Obtain a formal clarification and define an objective acceptance test.",
                               source_refs=m["refs"]) for m in key["mutants"]],
                questions=[dict(question="Which provision governs and who will approve the clarification?",
                                source_refs=m["refs"]) for m in key["mutants"][:2]],
                architecture=dict(approach="hybrid", components=["Service boundary", "Migration controls", "Differential tests"],
                                  rationale="A provisional approach pending source discovery and verified dependency evidence."))


def plan_cases(seed: int, n_test: int) -> list[dict]:
    if not 1 <= n_test <= 100:
        raise ValueError("The catalogue supports between 1 and 100 test projects.")
    return [dict(index=i, role="calibration" if i == 0 else "test") for i in range(n_test + 1)]


def write_batch(seed: int, n_test: int, out: Path, sealed: Path,
                max_attempts: int = 120) -> list[dict]:
    """Write a new corpus; reject duplicate structures, ordering and template sets.

    Similarity is measured against unchanged thresholds and disclosed explicitly.
    A generated batch failing these thresholds is not suitable for sealing.
    """
    import independence_audit as audit
    if (out / "case_pack.json").exists():
        raise FileExistsError(f"Refusing to replace an existing corpus: {out}")
    plans = plan_cases(seed, n_test)
    cases, fingerprints = [], []
    for plan in plans:
        for attempt in range(max_attempts):
            case = generate_case(seed, **plan, attempt=attempt)
            fp = (audit.heading_skeleton(case["rfp"]), audit.kind_sequence(case["key"]),
                  frozenset(m["template"] for m in case["key"]["mutants"]))
            if any(any(fp[j] == previous[j] for j in range(3)) for previous in fingerprints):
                continue
            cases.append(case)
            fingerprints.append(fp)
            break
        else:
            raise RuntimeError(f"Could not find a structurally distinct case {plan['index']}")
    report = audit.audit(cases)
    (out / "rfp").mkdir(parents=True, exist_ok=True)
    (out / "calibration").mkdir(exist_ok=True)
    sealed.mkdir(parents=True, exist_ok=True)
    entries = []
    for case in cases:
        folder = "calibration" if case["role"] == "calibration" else "rfp"
        path = f"{folder}/RFP_{case['id']}.md"
        (out / path).write_text(case["rfp"], encoding="utf-8", newline="\n")
        filename = f"answer_key_{case['id']}.json"
        save_json(sealed / filename, case["key"])
        entries.append(dict(id=case["id"], domain=case["domain"], persona=case["persona"], role=case["role"],
                            rfp=path, answer_key=f"oracle/{filename}", synthetic=True,
                            independently_reviewed=False, reviewers=[], review_date=None))
    save_json(out / "case_pack.json", dict(schema_version=2, experiment="english-synthetic-v3", cases=entries))
    save_json(out / "public_manifest.json", dict(generator_version=GEN_VERSION, language="en",
              test_cases=n_test, calibration_cases=1,
              cases=[dict(id=c["id"], role=c["role"], rfp_sha256=sha256_text(c["rfp"]),
                          project=c["key"]["covariates"]["project"], persona=c["persona"]) for c in cases]))
    save_json(out / "diversity_audit.json", dict(metrics=report, thresholds_passed=not audit.check(report, {}),
              limitations=["Synthetic shared templates, not independent human authors.",
                           "English v3 is not the corpus evaluated in the historical article.",
                           "Structural diversity does not establish statistical independence."]))
    return cases


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sealed", type=Path, required=True)
    args = parser.parse_args()
    cases = write_batch(args.seed, args.n, args.out, args.sealed)
    print(f"Wrote {len(cases) - 1} English test RFPs and one calibration RFP.")


if __name__ == "__main__":
    main()
