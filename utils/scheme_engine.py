import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class DocumentSource:
    def __init__(
        self,
        url: str,
        title: str,
        organization: str,
        last_updated: str = "",
        contact: str = "",
    ) -> None:
        self.url = url
        self.title = title
        self.organization = organization
        self.last_updated = last_updated or datetime.now().isoformat()
        self.contact = contact
        self.id = hash(url + title + organization)


class GovernmentRAGSystem:
    """Comprehensive RAG system for government agricultural data retrieval"""

    def __init__(self):
        self.documents = []
        self.sources = {}
        self.initialize_mock_data()

    def initialize_mock_data(self):
        """Initialize with extensive mock government scheme data"""
        mock_sources = [
            DocumentSource(
                "https://pmkisan.gov.in/",
                "PM-KISAN Samman Nidhi",
                "Ministry of Agriculture & Farmers Welfare",
                "2024-01-15",
                "pmkisan-helpline@gov.in",
            ),
            DocumentSource(
                "https://pmfby.gov.in/",
                "Pradhan Mantri Fasal Bima Yojana",
                "Ministry of Agriculture & Farmers Welfare",
                "2024-02-20",
                "pmfby@gov.in",
            ),
            DocumentSource(
                "https://soilhealth.dac.gov.in/",
                "Soil Health Card Scheme",
                "Department of Agriculture, Cooperation & Farmers Welfare",
                "2024-03-10",
                "soilhealth@nic.in",
            ),
            DocumentSource(
                "https://mkisan.gov.in",
                "Kisan Credit Card (KCC)",
                "RBI / NABARD",
                "2024-01-30",
                "kcc@nabard.org",
            ),
            DocumentSource(
                "https://dahd.nic.in",
                "National Livestock Mission",
                "Department of Animal Husbandry & Dairying",
                "2024-02-15",
                "nlm@dahd.nic.in",
            ),
            DocumentSource(
                "https://pmmsy.dof.gov.in",
                "Pradhan Mantri Matsya Sampada Yojana",
                "Department of Fisheries",
                "2024-03-01",
                "pmmsy@fisheries.gov.in",
            ),
            DocumentSource(
                "https://mgnrega.nic.in",
                "Mahatma Gandhi NREGA",
                "Ministry of Rural Development",
                "2024-02-28",
                "mgnrega@nic.in",
            ),
            DocumentSource(
                "https://pmegp.gov.in",
                "Prime Minister's Employment Generation Programme",
                "Ministry of Micro, Small & Medium Enterprises",
                "2024-01-20",
                "pmegp@kviconline.gov.in",
            ),
            DocumentSource(
                "https://nhm.nic.in",
                "National Horticulture Mission",
                "Ministry of Agriculture & Farmers Welfare",
                "2024-02-10",
                "nhm@agriculture.gov.in",
            ),
            DocumentSource(
                "https://pmksy.gov.in",
                "Pradhan Mantri Krishi Sinchayee Yojana",
                "Ministry of Agriculture & Farmers Welfare",
                "2024-03-05",
                "pmksy@gov.in",
            ),
            DocumentSource(
                "https://paramparagat.in",
                "Paramparagat Krishi Vikas Yojana",
                "Ministry of Agriculture & Farmers Welfare",
                "2024-02-25",
                "pkvk@agriculture.gov.in",
            ),
            DocumentSource(
                "https://biotech.nic.in",
                "Biotech-KISAN",
                "Department of Biotechnology",
                "2024-01-18",
                "biotechkisan@dbt.nic.in",
            ),
        ]

        mock_documents = [
            {
                "scheme_id": "pm-kisan",
                "title": "PM-KISAN Samman Nidhi",
                "content": """
                Direct income support of ₹6,000 per year for small and marginal farmer families.
                Amount is transferred in 3 equal installments of ₹2,000 directly to bank accounts.
                Applicable for landholding families with cultivable land up to 2 hectares.
                Special provisions for North-Eastern states with relaxed criteria.
                Last date for enrollment: 31st March 2025.
                """,
                "source_id": mock_sources[0].id,
                "keywords": [
                    "income",
                    "money",
                    "support",
                    "6000",
                    "cash",
                    "small farmer",
                    "marginal",
                    "installment",
                    "direct benefit",
                ],
                "category": "Financial Support",
                "financial_benefit": "₹6,000 annually",
                "application_mode": "Online/Offline",
                "valid_until": "2025-03-31",
            },
            {
                "scheme_id": "crop-insurance",
                "title": "Pradhan Mantri Fasal Bima Yojana",
                "content": """
                Comprehensive crop insurance against natural calamities, pests, and diseases.
                Premium rates: 2% for Kharif crops, 1.5% for Rabi crops, 5% for horticultural crops.
                Covers pre-sowing to post-harvest losses. No upper limit on government subsidy.
                Special focus on loanee farmers. Use of technology for quick claim settlement.
                Enrollment period: Kharif - April to July, Rabi - October to December.
                """,
                "source_id": mock_sources[1].id,
                "keywords": [
                    "insurance",
                    "loss",
                    "damage",
                    "rain",
                    "pest",
                    "kharif",
                    "rabi",
                    "premium",
                    "calamity",
                    "coverage",
                ],
                "category": "Crop Insurance",
                "financial_benefit": "Premium subsidy up to 90%",
                "application_mode": "Bank/Branch",
                "valid_until": "2025-12-31",
            },
            {
                "scheme_id": "kcc",
                "title": "Kisan Credit Card (KCC)",
                "content": """
                Short-term credit for cultivation, harvest expenses, and produce marketing.
                Interest subvention of 2% and additional 3% for timely repayment.
                Credit limit based on landholding and cropping pattern.
                Covers working capital for agriculture and allied activities.
                Includes personal accident insurance cover of ₹50,000.
                """,
                "source_id": mock_sources[3].id,
                "keywords": [
                    "loan",
                    "credit",
                    "bank",
                    "money",
                    "debt",
                    "finance",
                    "interest",
                    "working capital",
                ],
                "category": "Credit & Finance",
                "financial_benefit": "Interest subvention up to 5%",
                "application_mode": "Bank/Branch",
                "valid_until": "2026-03-31",
            },
            {
                "scheme_id": "pmksy",
                "title": "Pradhan Mantri Krishi Sinchayee Yojana",
                "content": """
                Focus on 'Har Khet Ko Pani' and improving water use efficiency.
                Subsidy for drip/sprinkler irrigation: 55% for small farmers, 45% for others.
                Support for community irrigation projects and micro-irrigation.
                Per Drop More Crop component for precision irrigation.
                Convergence with MGNREGA for water conservation works.
                """,
                "source_id": mock_sources[9].id,
                "keywords": [
                    "irrigation",
                    "water",
                    "drip",
                    "sprinkler",
                    "conservation",
                    "harvesting",
                    "well",
                    "pond",
                ],
                "category": "Infrastructure",
                "financial_benefit": "Up to 55% subsidy",
                "application_mode": "Agriculture Department",
                "valid_until": "2026-03-31",
            },
            {
                "scheme_id": "pkvk",
                "title": "Paramparagat Krishi Vikas Yojana",
                "content": """
                Promotion of organic farming through cluster approach.
                Financial assistance of ₹50,000 per hectare over 3 years.
                Support for organic seed, certification, and marketing.
                Formation of Farmer Producer Organizations (FPOs).
                Training and capacity building for organic practices.
                """,
                "source_id": mock_sources[10].id,
                "keywords": [
                    "organic",
                    "natural",
                    "chemical-free",
                    "certification",
                    "cluster",
                    "bio-fertilizer",
                    "vermicompost",
                ],
                "category": "Organic Farming",
                "financial_benefit": "₹50,000/hectare over 3 years",
                "application_mode": "Agriculture Department",
                "valid_until": "2025-12-31",
            },
            {
                "scheme_id": "nhm",
                "title": "National Horticulture Mission",
                "content": """
                Integrated development of horticulture with backward and forward linkages.
                Subsidy for greenhouses: 50% for small farmers, 35% for others.
                Support for horticulture clusters, cold chains, and processing units.
                Mission for Integrated Development of Horticulture (MIDH) components.
                Focus on high-value crops and export promotion.
                """,
                "source_id": mock_sources[8].id,
                "keywords": [
                    "horticulture",
                    "fruits",
                    "vegetables",
                    "greenhouse",
                    "cold storage",
                    "processing",
                    "floriculture",
                ],
                "category": "Horticulture",
                "financial_benefit": "Up to 50% subsidy",
                "application_mode": "Horticulture Department",
                "valid_until": "2026-03-31",
            },
            {
                "scheme_id": "nlm",
                "title": "National Livestock Mission",
                "content": """
                Sustainable development of livestock sector.
                Subsidy for animal shelter: 50% for SC/ST, 33% for others.
                Support for feed and fodder development.
                Entrepreneurship development and breed improvement.
                Risk management and insurance support for livestock.
                """,
                "source_id": mock_sources[4].id,
                "keywords": [
                    "livestock",
                    "dairy",
                    "cattle",
                    "goat",
                    "poultry",
                    "sheep",
                    "fodder",
                    "animal husbandry",
                ],
                "category": "Livestock",
                "financial_benefit": "Up to 50% subsidy",
                "application_mode": "Animal Husbandry Department",
                "valid_until": "2025-12-31",
            },
            {
                "scheme_id": "pmmsy",
                "title": "Pradhan Mantri Matsya Sampada Yojana",
                "content": """
                Blue Revolution through sustainable development of fisheries.
                Subsidy for fishing boats: 50% for SC/ST/women, 40% for others.
                Support for aquaculture, mariculture, and fish processing.
                Cold chain infrastructure and market linkages.
                Insurance coverage for fishermen and aquaculture farmers.
                """,
                "source_id": mock_sources[5].id,
                "keywords": [
                    "fisheries",
                    "fish",
                    "aquaculture",
                    "fishing",
                    "boat",
                    "pond",
                    "marine",
                    "inland",
                ],
                "category": "Fisheries",
                "financial_benefit": "Up to 50% subsidy",
                "application_mode": "Fisheries Department",
                "valid_until": "2024-12-31",
            },
            {
                "scheme_id": "pmegp",
                "title": "Prime Minister's Employment Generation Programme",
                "content": """
                Generate employment through establishment of micro-enterprises.
                Maximum project cost: ₹25 lakh (manufacturing), ₹10 lakh (service).
                Margin money subsidy: 25-35% depending on category.
                Priority for SC/ST/OBC/women/PH/ex-servicemen/aspirational districts.
                Handholding support for 2 years after project setup.
                """,
                "source_id": mock_sources[7].id,
                "keywords": [
                    "employment",
                    "enterprise",
                    "business",
                    "startup",
                    "subsidy",
                    "project",
                    "manufacturing",
                ],
                "category": "Entrepreneurship",
                "financial_benefit": "25-35% subsidy",
                "application_mode": "KVIC/KVIB/DIC",
                "valid_until": "2025-03-31",
            },
            {
                "scheme_id": "mgnrega",
                "title": "Mahatma Gandhi National Rural Employment Guarantee Act",
                "content": """
                100 days of guaranteed wage employment in rural areas.
                Asset creation related to water conservation, drought relief, and irrigation.
                Worksite facilities including crèche, drinking water, and first aid.
                Unemployment allowance if work not provided within 15 days.
                Special provisions for women (1/3rd participation) and disabled persons.
                """,
                "source_id": mock_sources[6].id,
                "keywords": [
                    "employment",
                    "wages",
                    "rural",
                    "guarantee",
                    "work",
                    "labor",
                    "asset creation",
                ],
                "category": "Rural Employment",
                "financial_benefit": "Minimum ₹250/day",
                "application_mode": "Gram Panchayat",
                "valid_until": "Ongoing",
            },
            {
                "scheme_id": "soil-health",
                "title": "Soil Health Card Scheme",
                "content": """
                Get a report card on soil's nutrient status and fertilizer recommendations.
                Issued every 2 years to improve soil fertility and productivity.
                Testing for 12 parameters including macro and micro nutrients.
                SMS alerts for soil test results and fertilizer recommendations.
                Integration with PM-KISAN database for targeted delivery.
                """,
                "source_id": mock_sources[2].id,
                "keywords": [
                    "soil",
                    "test",
                    "nutrient",
                    "fertilizer",
                    "health",
                    "lab",
                    "testing",
                    "analysis",
                ],
                "category": "Advisory Services",
                "financial_benefit": "Free testing",
                "application_mode": "Agriculture Department/KVK",
                "valid_until": "2025-12-31",
            },
            {
                "scheme_id": "biotech-kisan",
                "title": "Biotech-KISAN Programme",
                "content": """
                Connecting science with farming through scientist-farmer partnership.
                Establishment of Biotech-KISAN Hubs in 15 agro-climatic zones.
                Training in modern biotechnology tools for agriculture.
                Support for soil-less cultivation, hydroponics, and bio-fortification.
                Special focus on women farmers and North-Eastern regions.
                """,
                "source_id": mock_sources[11].id,
                "keywords": [
                    "biotech",
                    "technology",
                    "innovation",
                    "research",
                    "science",
                    "modern",
                    "hydroponics",
                ],
                "category": "Technology",
                "financial_benefit": "Technical support",
                "application_mode": "Research Institutions",
                "valid_until": "2025-03-31",
            },
            {
                "scheme_id": "e-nam",
                "title": "National Agriculture Market (e-NAM)",
                "content": "A pan-India electronic trading portal which networks the existing Agricultural Produce Market Committees (APMCs) to create a unified national market for agricultural commodities. It enables transparent price discovery, facilitates competitive bidding, and allows farmers to sell produce across state borders.",
                "source_id": mock_sources[0].id,
                "keywords": [
                    "market",
                    "online",
                    "trading",
                    "price",
                    "APMC",
                    "e-market",
                ],
                "category": "Marketing & Trade",
                "financial_benefit": "Better price realization",
                "application_mode": "Online Portal",
                "valid_until": "Ongoing",
            },
            {
                "scheme_id": "pm-kusum",
                "title": "Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan (PM-KUSUM)",
                "content": "Aims to increase farmers' income and ensure their energy security through solar power. The scheme has three components: installing standalone solar pumps, solarizing existing grid-connected agricultural pumps, and setting up solar power plants on barren/fallow land.",
                "source_id": mock_sources[0].id,
                "keywords": [
                    "solar",
                    "energy",
                    "pump",
                    "green",
                    "subsidy",
                    "renewable",
                ],
                "category": "Infrastructure / Green Energy",
                "financial_benefit": "Up to 60% subsidy",
                "application_mode": "State Agriculture Departments",
                "valid_until": "2026-03-31",
            },
            {
                "scheme_id": "smam",
                "title": "Sub-Mission on Agricultural Mechanization (SMAM)",
                "content": "Promotes agricultural mechanization among small and marginal farmers. Provides subsidies for purchasing a wide range of agricultural machinery and equipment. Aims to reduce drudgery, improve efficiency, and lower the cost of cultivation.",
                "source_id": mock_sources[0].id,
                "keywords": [
                    "machinery",
                    "tractor",
                    "equipment",
                    "subsidy",
                    "productivity",
                    "tools",
                ],
                "category": "Technology & Equipment",
                "financial_benefit": "Up to 50% subsidy",
                "application_mode": "DBT Portal / State Nodal Agencies",
                "valid_until": "2025-12-31",
            },
            {
                "scheme_id": "vb-gram",
                "title": "Viksit Bharat - Rozgar And Ajeevika Mission (Gramin) (VB-G RAM G)",
                "content": "A proposed new central law aimed at replacing MGNREGA. It guarantees 125 days of wage employment per financial year to adult members of rural households in areas notified by the central government. It shifts the framework from a demand-driven to a supply-driven employment program.",
                "source_id": mock_sources[6].id,
                "keywords": [
                    "employment",
                    "wages",
                    "rural",
                    "guarantee",
                    "125 days",
                    "viksit bharat",
                ],
                "category": "Rural Employment",
                "financial_benefit": "Minimum wages for 125 days/year",
                "application_mode": "Gram Panchayat / Local Administration",
                "valid_until": "Proposed",
            },
            {
                "scheme_id": "agri-infra-fund",
                "title": "Agriculture Infrastructure Fund (AIF)",
                "content": "Provides medium to long-term debt financing for viable projects for post-harvest management infrastructure and community farming assets. Offers a credit guarantee and interest subvention to eligible beneficiaries.",
                "source_id": mock_sources[0].id,
                "keywords": [
                    "loan",
                    "infrastructure",
                    "warehouse",
                    "cold storage",
                    "processing",
                    "interest subvention",
                ],
                "category": "Infrastructure",
                "financial_benefit": "Loans with interest subvention",
                "application_mode": "Banks",
                "valid_until": "2032-03-31",
            },
        ]

        state_schemes = [
            {
                "scheme_id": "raithu-bandhu-telangana",
                "title": "Rythu Bandhu Scheme (Telangana)",
                "content": "Investment support of ₹10,000 per acre per year for agriculture and horticulture crops. Two installments: Rabi and Kharif seasons.",
                "source_id": mock_sources[0].id,
                "keywords": [
                    "telangana",
                    "investment",
                    "support",
                    "per acre",
                    "raithu",
                    "rythu",
                ],
                "category": "State Financial Support",
                "financial_benefit": "₹10,000/acre/year",
                "application_mode": "Agriculture Department",
                "valid_until": "Ongoing",
            },
            {
                "scheme_id": "krishak-bandhu-westbengal",
                "title": "Krishak Bandhu Scheme (West Bengal)",
                "content": "Annual assistance of ₹5,000 per acre (max 2 acres) + ₹2 lakh death benefit. For small and marginal farmers.",
                "source_id": mock_sources[0].id,
                "keywords": ["west bengal", "assistance", "death benefit", "krishak"],
                "category": "State Financial Support",
                "financial_benefit": "₹5,000/acre + insurance",
                "application_mode": "Agriculture Department",
                "valid_until": "2025-03-31",
            },
        ]

        mock_documents.extend(state_schemes)

        for source in mock_sources:
            self.sources[source.id] = source

        self.documents = mock_documents

    def search_schemes(
        self, query: str, user_profile: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Enhanced search:
        - If query exists: Keyword/Semantic search -> Filter by Eligibility
        - If query empty: Check Eligibility on ALL docs -> Return Eligible ones first
        """
        query_lower = query.lower().strip()
        results = []

        if not query_lower:
            docs_to_process = [(doc, 1.0) for doc in self.documents]
        else:
            docs_to_check = []
            for doc in self.documents:
                score = self._calculate_relevance_score(doc, query_lower)
                if score > 0.3:
                    docs_to_check.append((doc, score))
            docs_to_process = docs_to_check

        for doc, search_score in docs_to_process:
            source = self.sources[doc["source_id"]]

            is_eligible = True
            eligibility_note = "General eligibility."
            benefits = []
            required_docs = []

            if user_profile:
                (
                    is_eligible,
                    eligibility_note,
                    benefits,
                    required_docs,
                ) = self._check_eligibility(doc["scheme_id"], user_profile)

            final_score = search_score
            if is_eligible:
                final_score += 0.5

            if user_profile and not query_lower:
                priority_score = self._calculate_profile_relevance(doc, user_profile)
                final_score += priority_score

            results.append(
                {
                    "id": doc["scheme_id"],
                    "title": doc["title"],
                    "description": doc["content"],
                    "category": doc["category"],
                    "score": final_score,
                    "source_url": source.url,
                    "source_organization": source.organization,
                    "financial_benefit": doc.get("financial_benefit", ""),
                    "is_eligible": is_eligible,
                    "eligibility_note": eligibility_note,
                    "special_benefits": benefits,
                    "required_documents": required_docs,
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:20]

    def _calculate_profile_relevance(self, doc: Dict, profile: Dict) -> float:
        """Helper to calculate how relevant a scheme is to the user's specific profile"""
        score = 0.0
        crops = [c.lower() for c in profile.get("crops", [])]
        doc_content = doc["content"].lower()

        for crop in crops:
            if crop in doc_content:
                score += 0.2

        state = profile.get("state", "").lower()
        if state and state in doc_content:
            score += 0.3

        land_size = float(profile.get("land_size", 0) or 0)
        if land_size <= 2 and "small" in doc_content:
            score += 0.1

        return score

    def _calculate_relevance_score(self, doc: Dict, query: str) -> float:
        """Calculate relevance score between document and query"""
        score = 0.0

        if query in doc["title"].lower():
            score += 0.4

        content_lower = doc["content"].lower()
        if query in content_lower:
            score += 0.3

        for keyword in doc["keywords"]:
            if keyword in query:
                score += 0.1
            if query in keyword:
                score += 0.15

        if query in doc["category"].lower():
            score += 0.2

        query_words = query.split()
        for word in query_words:
            if len(word) > 3 and word in content_lower:
                score += 0.05

        return min(score, 1.0)

    def _check_eligibility(
        self, scheme_id: str, profile: Dict
    ) -> Tuple[bool, str, List[str], List[str]]:
        """Comprehensive eligibility checking with detailed criteria"""
        land_size = float(profile.get("land_size", 0) or 0)
        income = float(profile.get("annual_income", 0) or 0)
        caste = profile.get("caste", "").upper()
        gender = profile.get("gender", "").upper()
        age = int(profile.get("age", 0) or 0)
        state = profile.get("state", "").lower()
        is_tenant = profile.get("is_tenant", False)
        has_bank_account = profile.get("has_bank_account", True)
        crops = [c.lower() for c in profile.get("crops", [])]

        benefits = []
        required_docs = ["Aadhaar Card", "Bank Passbook", "Land Record"]

        if scheme_id == "pm-kisan":
            if land_size > 2:
                return False, "Landholding exceeds 2 hectares limit.", [], required_docs
            if income > 100000:
                return (
                    False,
                    "Annual family income exceeds ₹1,00,000 limit.",
                    [],
                    required_docs,
                )
            if not has_bank_account:
                return (
                    False,
                    "Bank account required for direct benefit transfer.",
                    [],
                    required_docs,
                )

            benefits = [
                "₹6,000 annual support",
                "Direct bank transfer",
                "Three installments",
            ]
            required_docs.extend(["Land ownership proof", "Aadhaar-linked mobile"])

            if caste in ["SC", "ST"]:
                benefits.append("Priority processing")
            if gender == "FEMALE":
                benefits.append("Women farmer incentive")

            return (
                True,
                f"Eligible for PM-KISAN (Land: {land_size} ha)",
                benefits,
                required_docs,
            )

        elif scheme_id == "crop-insurance":
            if land_size < 0.1:
                return (
                    False,
                    "Minimum landholding of 0.1 hectares required.",
                    [],
                    required_docs,
                )
            if not crops:
                return False, "Must be cultivating notified crops.", [], required_docs

            benefits = ["Premium subsidy", "Comprehensive coverage", "Quick claims"]
            required_docs.extend(["Crop details", "Land record", "Sowing declaration"])

            if caste in ["SC", "ST"]:
                benefits.append("Additional premium concession")
            if is_tenant:
                required_docs.append("Tenancy agreement")

            return True, "Eligible for crop insurance", benefits, required_docs

        elif scheme_id == "kcc":
            if age < 18 or age > 75:
                return False, "Age must be between 18-75 years.", [], required_docs
            if land_size == 0 and not is_tenant:
                return (
                    False,
                    "Land ownership or tenancy proof required.",
                    [],
                    required_docs,
                )

            credit_limit = min(land_size * 50000, 300000)
            benefits = [
                f"Credit limit up to ₹{credit_limit:,}",
                "Interest subvention",
                "Insurance cover",
            ]
            required_docs.extend(["Land records", "Crop pattern", "Identity proof"])

            if caste in ["SC", "ST"]:
                benefits.append("Margin money concession")
            if gender == "FEMALE":
                benefits.append("Lower interest rate")

            return (
                True,
                f"Eligible for KCC with credit limit up to ₹{credit_limit:,}",
                benefits,
                required_docs,
            )

        elif scheme_id == "raithu-bandhu-telangana":
            if state != "telangana":
                return (
                    False,
                    "Only available for Telangana residents.",
                    [],
                    required_docs,
                )
            return (
                True,
                "Eligible for Rythu Bandhu",
                ["₹10,000/acre/year"],
                required_docs,
            )

        elif scheme_id == "krishak-bandhu-westbengal":
            if state != "west bengal":
                return (
                    False,
                    "Only available for West Bengal residents.",
                    [],
                    required_docs,
                )
            if land_size > 2:
                return False, "Maximum 2 acres eligible.", [], required_docs
            return (
                True,
                "Eligible for Krishak Bandhu",
                ["₹5,000/acre + insurance"],
                required_docs,
            )

        benefits = ["Check with local department for specific benefits"]
        return (
            True,
            "Generally eligible. Verify with department for exact criteria.",
            benefits,
            required_docs,
        )

    def get_recommendations(self, user_profile: Optional[Dict] = None) -> List[Dict]:
        """Get personalized scheme recommendations"""
        if not user_profile:
            return self.documents[:5]

        recommendations = []
        land_size = float(user_profile.get("land_size", 0) or 0)
        crops = [c.lower() for c in user_profile.get("crops", [])]

        for doc in self.documents:
            priority = 0

            if land_size <= 2 and doc["category"] == "Financial Support":
                priority += 3

            doc_content = doc["content"].lower()
            for crop in crops:
                if crop in doc_content:
                    priority += 2

            if doc["scheme_id"] == "crop-insurance" and any(
                c in ["paddy", "cotton", "sugarcane"] for c in crops
            ):
                priority += 2

            if 2 < land_size <= 5 and doc["category"] == "Credit & Finance":
                priority += 2

            if priority > 0:
                recommendations.append(doc)

        return recommendations[:8] if recommendations else self.documents[:5]

    def filter_schemes(self, filters: Dict) -> List[Dict]:
        """Filter schemes based on multiple criteria"""
        filtered = []

        for doc in self.documents:
            matches = True

            if "category" in filters and filters["category"] != doc["category"]:
                matches = False
            if "state" in filters and "state" in doc.get("keywords", []):
                state_keywords = [
                    filters["state"].lower(),
                    filters["state"].lower().replace(" ", ""),
                ]
                if not any(keyword in doc["keywords"] for keyword in state_keywords):
                    matches = False
            if "financial_min" in filters:
                benefit = doc.get("financial_benefit", "0")
                amount = self._extract_amount(benefit)
                if amount < filters["financial_min"]:
                    matches = False

            if matches:
                filtered.append(doc)

        return filtered

    def _extract_amount(self, text: str) -> float:
        """Extract numerical amount from text"""
        matches = re.findall(r"₹?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", text)
        if matches:
            return float(matches[0].replace(",", ""))
        return 0.0

    def get_scheme_details(self, scheme_id: str) -> Optional[Dict]:
        """Get complete details of a specific scheme"""
        for doc in self.documents:
            if doc["scheme_id"] == scheme_id:
                source = self.sources[doc["source_id"]]
                return {
                    **doc,
                    "source_url": source.url,
                    "organization": source.organization,
                    "contact": source.contact,
                    "last_updated": source.last_updated,
                }
        return None


scheme_engine = GovernmentRAGSystem()
