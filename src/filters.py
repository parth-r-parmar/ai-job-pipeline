"""Job filtering — salary parsing, internship exclusion, product-company detection."""

import re
import logging

from src.config import MIN_SALARY_LPA, EXCLUDE_INTERNSHIPS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known product-based companies (Indian tech ecosystem)
# ---------------------------------------------------------------------------
KNOWN_PRODUCT_COMPANIES = {
    # Large product companies
    "google", "microsoft", "amazon", "apple", "meta", "netflix", "uber",
    "flipkart", "swiggy", "zomato", "razorpay", "zerodha", "cred",
    "phonepe", "paytm", "groww", "meesho", "sharechat", "dream11",
    "ola", "rapido", "dunzo", "lenskart", "nykaa", "mamaearth",
    "freshworks", "zoho", "postman", "browserstack", "chargebee",
    "clevertap", "druva", "icertis", "innovaccer", "leadsquared",
    "mindtickle", "moglix", "moengage", "yellowai", "yellow.ai",
    "unacademy", "upgrad", "vedantu", "byjus", "byju's", "toppr",
    "juspay", "rupeek", "slice", "jupiter", "fi", "smallcase",
    "instamojo", "shiprocket", "delhivery", "rivigo", "blackbuck",
    "urban company", "urbancompany", "practo", "1mg", "healthkart",
    "spinny", "cars24", "cardekho", "ola electric",
    "atlassian", "notion", "figma", "vercel", "supabase", "stripe",
    "twilio", "datadog", "elastic", "gitlab", "hashicorp",
    "hotstar", "disney+ hotstar", "jio", "reliance jio",
    "samsung", "intel", "nvidia", "adobe", "salesforce", "oracle",
    "shopify", "spotify", "slack", "discord", "linkedin",
    # Mid-size product companies
    "vagaro", "appscrip", "gupshup", "haptik", "niki.ai",
    "servify", "toplyne", "rocketlane", "wingify", "webengage",
    "netcore", "insider", "helpshift",
}

# Service/consulting companies (for contrast — flag as service-based)
KNOWN_SERVICE_COMPANIES = {
    "tcs", "infosys", "wipro", "hcl", "hcltech", "tech mahindra",
    "cognizant", "accenture", "capgemini", "deloitte", "kpmg", "ey",
    "pwc", "mindtree", "mphasis", "ltimindtree", "lti", "hexaware",
    "cyient", "persistent", "zensar", "birlasoft", "niit",
    "l&t infotech", "coforge",
}


def parse_salary_lpa(salary_str: str) -> float | None:
    """Parse an Indian salary string and return the value in LPA.

    Handles formats:
    - "₹ 4,50,000 - 6,00,000"  → 6.0 (takes upper bound)
    - "₹ 8,00,000 /year"       → 8.0
    - "8-12 LPA"                → 12.0
    - "10 LPA"                  → 10.0
    - "₹ 80,000 /month"        → 9.6
    - "Not disclosed"           → None
    - "Competitive salary"      → None
    """
    if not salary_str or salary_str in ("Not disclosed", "N/A", "Competitive salary"):
        return None

    s = salary_str.replace("₹", "").replace(",", "").replace("\u20b9", "").strip()

    # Check for "X LPA" or "X-Y LPA" pattern
    lpa_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?)\s*)?(?:lpa|lakhs?|lac)", s, re.I)
    if lpa_match:
        return float(lpa_match.group(2) or lpa_match.group(1))

    # Check for monthly salary
    month_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*month", s, re.I)
    if month_match:
        monthly = float(month_match.group(1))
        return round(monthly * 12 / 100000, 1)

    # Check for annual amounts (Indian notation: 4,50,000 = 450000)
    # After stripping commas, find all numbers
    amounts = re.findall(r"\d{5,}", s)
    if amounts:
        # Take the highest amount (upper bound of range)
        max_amount = max(int(a) for a in amounts)
        # Check if it looks like /year or annual
        if "/year" in salary_str.lower() or len(amounts) >= 1:
            return round(max_amount / 100000, 1)

    return None


def classify_company(company_name: str) -> str:
    """Classify company as 'product', 'service', or 'unknown'."""
    name_lower = company_name.lower().strip()

    for known in KNOWN_PRODUCT_COMPANIES:
        if known in name_lower or name_lower in known:
            return "product"

    for known in KNOWN_SERVICE_COMPANIES:
        if known in name_lower or name_lower in known:
            return "service"

    return "unknown"


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Apply all configured filters. Returns filtered list and logs stats."""
    original_count = len(jobs)
    filtered = []
    removed_salary = 0
    removed_internship = 0

    for job in jobs:
        # Filter internships
        if EXCLUDE_INTERNSHIPS:
            jtype = job.get("job_type", "").lower()
            title = job.get("title", "").lower()
            if "intern" in jtype or "internship" in jtype:
                removed_internship += 1
                continue
            if title.startswith("intern ") or title.endswith(" intern") or "internship" in title:
                removed_internship += 1
                continue

        # Filter by salary
        salary_lpa = parse_salary_lpa(job.get("salary", ""))
        job["salary_lpa"] = salary_lpa  # store parsed value for sorting
        if salary_lpa is not None and salary_lpa < MIN_SALARY_LPA:
            removed_salary += 1
            continue

        # Classify company type
        job["company_type"] = classify_company(job.get("company", ""))

        filtered.append(job)

    logger.info(
        f"Filters applied: {original_count} → {len(filtered)} jobs "
        f"(removed {removed_internship} internships, {removed_salary} below {MIN_SALARY_LPA} LPA)"
    )
    return filtered
