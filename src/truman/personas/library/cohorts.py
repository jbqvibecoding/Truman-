"""Built-in cohort archetypes (PRD v2.0 §4.3.2).

A Cohort is a named audience template with N labeled segments. Each segment
("SegmentArchetype") is a probability distribution over Persona attributes:
the loader samples deterministically from these pools given a seed so runs
are reproducible.

Six built-in cohorts cover the seven application domains (PRD §2.2):
- `ad_segments`     → B / D (ad creative, landing pages)
- `social_segments` → C   (viral content)
- `us_swing_voters` → cross-domain (political messaging)
- `developer_personas` → A   (software engineering)
- `ecommerce_shoppers` → G  (PDP, landing pages)
- `email_audiences` → D / E (cold email, sales)
- `b2b_buyers`      → E    (sales scripts)
- `prd_readers`     → F    (PRDs, product docs)

The per-segment attribute pools (MBTI / country / profession / topics /
stance / influence) were lightly ported from MiroFish's
`oasis_profile_generator.py:156-180` + `:774-845` rule-based profile
generator (entity-type → activity_level / influence_weight) and condensed
into Truman's Persona shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SegmentArchetype:
    """One labeled audience archetype within a Cohort.

    The pools encode "what's typical" for this segment. The loader samples
    one value from each pool per generated persona.
    """

    label: str
    description: str
    mbti_pool: list[str]
    country_pool: list[str]
    profession_pool: list[str]
    interest_topics: list[str]
    sentiment_bias_range: tuple[float, float] = (-0.2, 0.6)
    influence_weight_range: tuple[float, float] = (0.7, 1.5)
    stance_dist: dict[str, float] = field(default_factory=lambda: {"enthusiast": 0.4, "neutral": 0.4, "skeptic": 0.2})


@dataclass(frozen=True)
class Cohort:
    """A named audience composition — a list of segment archetypes."""

    name: str
    description: str
    segments: list[SegmentArchetype]


# ─────────────────────── Cohort definitions ─────────────────────────────────


_AD_SEGMENTS = Cohort(
    name="ad_segments",
    description="Short-form video ad target audience: 5 high-conversion segments.",
    segments=[
        SegmentArchetype(
            label="小红书用户",
            description="Chinese lifestyle-app users; aesthetic-driven, recommendation-driven.",
            mbti_pool=["ENFP", "ESFJ", "ISFJ", "INFP"],
            country_pool=["CN", "SG", "MY"],
            profession_pool=["student", "creator", "designer", "office worker"],
            interest_topics=["lifestyle", "beauty", "travel deals", "aesthetics", "shopping"],
            sentiment_bias_range=(0.0, 0.7),
            influence_weight_range=(0.8, 1.4),
            stance_dist={"enthusiast": 0.55, "neutral": 0.35, "skeptic": 0.1},
        ),
        SegmentArchetype(
            label="TikTok用户",
            description="Global short-form video natives; trend-chasers, attention-thin.",
            mbti_pool=["ENFP", "ESTP", "ENTP", "ESFP"],
            country_pool=["US", "UK", "BR", "ID", "JP"],
            profession_pool=["student", "creator", "service worker", "freelancer"],
            interest_topics=["trends", "entertainment", "music", "memes", "challenges"],
            sentiment_bias_range=(-0.1, 0.6),
            influence_weight_range=(1.0, 2.0),
            stance_dist={"enthusiast": 0.5, "neutral": 0.3, "skeptic": 0.2},
        ),
        SegmentArchetype(
            label="美国宝妈",
            description="US moms 28-45: practical, deal-aware, family-first.",
            mbti_pool=["ESFJ", "ISFJ", "ENFJ", "INFJ"],
            country_pool=["US"],
            profession_pool=["parent", "teacher", "nurse", "retail manager", "freelancer"],
            interest_topics=["family", "deals", "kids", "health", "home", "savings"],
            sentiment_bias_range=(0.0, 0.6),
            influence_weight_range=(0.9, 1.5),
            stance_dist={"enthusiast": 0.4, "neutral": 0.4, "skeptic": 0.2},
        ),
        SegmentArchetype(
            label="Web3 Degens",
            description="Crypto-native early adopters: skeptical of marketing, FOMO-prone.",
            mbti_pool=["INTJ", "INTP", "ENTP", "ENTJ"],
            country_pool=["US", "SG", "DE", "global"],
            profession_pool=["engineer", "trader", "founder", "researcher"],
            interest_topics=["crypto", "defi", "airdrops", "alpha", "memes", "tech"],
            sentiment_bias_range=(-0.4, 0.3),
            influence_weight_range=(1.2, 2.0),
            stance_dist={"enthusiast": 0.3, "neutral": 0.3, "skeptic": 0.4},
        ),
        SegmentArchetype(
            label="GenZ",
            description="16-26: identity-aware, ironic, anti-cringe, climate-conscious.",
            mbti_pool=["INFP", "ENFP", "INTP", "ISFP"],
            country_pool=["US", "UK", "AU", "CA"],
            profession_pool=["student", "intern", "creator", "service worker"],
            interest_topics=["identity", "sustainability", "music", "games", "memes", "mental health"],
            sentiment_bias_range=(-0.3, 0.4),
            influence_weight_range=(0.8, 1.4),
            stance_dist={"enthusiast": 0.3, "neutral": 0.4, "skeptic": 0.3},
        ),
    ],
)


_SOCIAL_SEGMENTS = Cohort(
    name="social_segments",
    description="Viral-content audience across 6 platforms / sub-communities.",
    segments=[
        SegmentArchetype(
            label="Reddit user",
            description="Niche-community lurker; sniffs out astroturf instantly.",
            mbti_pool=["INTJ", "INTP", "ISTP", "ENTP"],
            country_pool=["US", "UK", "CA", "DE"],
            profession_pool=["engineer", "student", "analyst", "researcher"],
            interest_topics=["discussion", "tech", "science", "memes", "hot takes"],
            sentiment_bias_range=(-0.4, 0.3),
            influence_weight_range=(0.7, 1.4),
            stance_dist={"enthusiast": 0.2, "neutral": 0.4, "skeptic": 0.4},
        ),
        SegmentArchetype(
            label="Twitter user",
            description="News-junky, hot-take poster, high virality multiplier.",
            mbti_pool=["ENTP", "INTJ", "ENTJ", "ESTP"],
            country_pool=["US", "UK", "JP", "IN"],
            profession_pool=["journalist", "founder", "analyst", "creator"],
            interest_topics=["news", "politics", "tech", "hot takes", "drama"],
            sentiment_bias_range=(-0.3, 0.5),
            influence_weight_range=(1.3, 2.5),
            stance_dist={"enthusiast": 0.4, "neutral": 0.3, "skeptic": 0.3},
        ),
        SegmentArchetype(
            label="小红书 女生",
            description="Chinese lifestyle female user; aspirational, recommendation-friendly.",
            mbti_pool=["ENFP", "ESFJ", "INFJ"],
            country_pool=["CN"],
            profession_pool=["student", "designer", "creator", "office worker"],
            interest_topics=["lifestyle", "beauty", "wellness", "travel", "fashion"],
            sentiment_bias_range=(0.1, 0.7),
            influence_weight_range=(0.9, 1.5),
            stance_dist={"enthusiast": 0.55, "neutral": 0.3, "skeptic": 0.15},
        ),
        SegmentArchetype(
            label="Web3 KOL",
            description="Thought leader in crypto; their RT can move markets.",
            mbti_pool=["ENTJ", "ENTP", "INTJ"],
            country_pool=["US", "SG", "AE", "CH"],
            profession_pool=["founder", "VC", "trader", "researcher"],
            interest_topics=["crypto", "tokenomics", "alpha", "venture", "DeFi"],
            sentiment_bias_range=(-0.1, 0.5),
            influence_weight_range=(1.8, 3.0),
            stance_dist={"enthusiast": 0.5, "neutral": 0.3, "skeptic": 0.2},
        ),
        SegmentArchetype(
            label="黑粉",
            description="Contrarian hater; engagement-positive but sentiment-negative.",
            mbti_pool=["INTJ", "ISTP", "ENTJ", "ENTP"],
            country_pool=["US", "UK", "CN", "BR"],
            profession_pool=["unemployed", "student", "freelancer", "blogger"],
            interest_topics=["drama", "callouts", "hot takes", "criticism"],
            sentiment_bias_range=(-0.9, -0.2),
            influence_weight_range=(0.7, 1.6),
            stance_dist={"enthusiast": 0.05, "neutral": 0.15, "skeptic": 0.8},
        ),
        SegmentArchetype(
            label="路人",
            description="Casual scroller; low engagement floor but high reach if hooked.",
            mbti_pool=["ESFJ", "ISFJ", "ESFP", "ISFP"],
            country_pool=["US", "UK", "BR", "ID", "MX"],
            profession_pool=["service worker", "office worker", "student", "retiree"],
            interest_topics=["entertainment", "news", "lifestyle", "casual"],
            sentiment_bias_range=(-0.1, 0.4),
            influence_weight_range=(0.5, 1.0),
            stance_dist={"enthusiast": 0.25, "neutral": 0.55, "skeptic": 0.2},
        ),
    ],
)


_US_SWING_VOTERS = Cohort(
    name="us_swing_voters",
    description="US 2024-style swing-state voters across 5 battleground states.",
    segments=[
        SegmentArchetype(
            label="PA blue-collar",
            description="Pennsylvania working-class; economy-first, suspicious of elites.",
            mbti_pool=["ISTJ", "ESTJ", "ISFJ"],
            country_pool=["US"],
            profession_pool=["factory worker", "trucker", "service worker", "tradesman"],
            interest_topics=["jobs", "economy", "manufacturing", "fuel prices", "borders"],
            sentiment_bias_range=(-0.4, 0.2),
            influence_weight_range=(0.9, 1.3),
            stance_dist={"enthusiast": 0.25, "neutral": 0.4, "skeptic": 0.35},
        ),
        SegmentArchetype(
            label="MI auto worker",
            description="Michigan auto industry; union-influenced, EV-anxiety.",
            mbti_pool=["ISTJ", "ISFJ", "ESTJ"],
            country_pool=["US"],
            profession_pool=["auto worker", "union steward", "machinist", "supervisor"],
            interest_topics=["jobs", "auto industry", "EV transition", "trade", "healthcare"],
            sentiment_bias_range=(-0.3, 0.3),
            influence_weight_range=(0.9, 1.4),
            stance_dist={"enthusiast": 0.3, "neutral": 0.4, "skeptic": 0.3},
        ),
        SegmentArchetype(
            label="WI rural",
            description="Wisconsin small-town/farm; community-rooted, traditional.",
            mbti_pool=["ISFJ", "ESFJ", "ISTJ"],
            country_pool=["US"],
            profession_pool=["farmer", "small business owner", "teacher", "retiree"],
            interest_topics=["agriculture", "rural infrastructure", "trade", "guns", "faith"],
            sentiment_bias_range=(-0.2, 0.3),
            influence_weight_range=(0.8, 1.3),
            stance_dist={"enthusiast": 0.3, "neutral": 0.45, "skeptic": 0.25},
        ),
        SegmentArchetype(
            label="GA suburban",
            description="Georgia metro-Atlanta suburbs; mixed professional, education-aware.",
            mbti_pool=["ENFJ", "ESFJ", "INFJ", "ENFP"],
            country_pool=["US"],
            profession_pool=["teacher", "nurse", "engineer", "manager", "parent"],
            interest_topics=["schools", "housing", "healthcare", "crime", "abortion"],
            sentiment_bias_range=(-0.1, 0.4),
            influence_weight_range=(1.0, 1.5),
            stance_dist={"enthusiast": 0.35, "neutral": 0.4, "skeptic": 0.25},
        ),
        SegmentArchetype(
            label="AZ retiree",
            description="Arizona 55+; healthcare and inflation-sensitive.",
            mbti_pool=["ISFJ", "ESFJ", "ISTJ"],
            country_pool=["US"],
            profession_pool=["retiree", "former teacher", "former engineer", "veteran"],
            interest_topics=["healthcare", "social security", "inflation", "borders", "crime"],
            sentiment_bias_range=(-0.3, 0.3),
            influence_weight_range=(0.7, 1.2),
            stance_dist={"enthusiast": 0.3, "neutral": 0.4, "skeptic": 0.3},
        ),
    ],
)


_DEVELOPER_PERSONAS = Cohort(
    name="developer_personas",
    description="Code-review and adoption audience across 5 developer roles.",
    segments=[
        SegmentArchetype(
            label="junior dev",
            description="22-28; learning, eager, low risk-tolerance.",
            mbti_pool=["INTP", "INFP", "ENFP"],
            country_pool=["US", "IN", "UK", "DE", "BR"],
            profession_pool=["junior engineer", "bootcamp grad", "intern"],
            interest_topics=["learning", "tutorials", "best practices", "new tech"],
            sentiment_bias_range=(0.1, 0.6),
            influence_weight_range=(0.5, 1.0),
            stance_dist={"enthusiast": 0.55, "neutral": 0.35, "skeptic": 0.1},
        ),
        SegmentArchetype(
            label="senior dev",
            description="30-45; pragmatic, allergic to over-engineering.",
            mbti_pool=["INTJ", "INTP", "ISTJ"],
            country_pool=["US", "UK", "DE", "JP"],
            profession_pool=["senior engineer", "tech lead", "staff engineer"],
            interest_topics=["architecture", "mentoring", "perf", "code quality", "maintainability"],
            sentiment_bias_range=(-0.2, 0.4),
            influence_weight_range=(1.2, 1.8),
            stance_dist={"enthusiast": 0.3, "neutral": 0.4, "skeptic": 0.3},
        ),
        SegmentArchetype(
            label="architect",
            description="35-55; systems-level concerns, distrustful of magic.",
            mbti_pool=["INTJ", "INTP"],
            country_pool=["US", "UK", "DE"],
            profession_pool=["principal engineer", "architect", "director of eng"],
            interest_topics=["systems design", "scaling", "data flow", "tradeoffs", "tech debt"],
            sentiment_bias_range=(-0.3, 0.3),
            influence_weight_range=(1.6, 2.4),
            stance_dist={"enthusiast": 0.2, "neutral": 0.4, "skeptic": 0.4},
        ),
        SegmentArchetype(
            label="devops",
            description="28-45; reliability-first, ops-burned.",
            mbti_pool=["ISTJ", "INTJ", "ISTP"],
            country_pool=["US", "UK", "DE", "IN"],
            profession_pool=["SRE", "devops engineer", "platform engineer"],
            interest_topics=["reliability", "monitoring", "CI/CD", "infra", "security"],
            sentiment_bias_range=(-0.3, 0.3),
            influence_weight_range=(1.0, 1.5),
            stance_dist={"enthusiast": 0.25, "neutral": 0.45, "skeptic": 0.3},
        ),
        SegmentArchetype(
            label="security reviewer",
            description="30-45; paid to be paranoid.",
            mbti_pool=["ISTJ", "INTJ"],
            country_pool=["US", "UK", "DE", "IL"],
            profession_pool=["security engineer", "appsec", "pentester", "auditor"],
            interest_topics=["security", "supply chain", "secrets", "auth", "compliance"],
            sentiment_bias_range=(-0.5, 0.2),
            influence_weight_range=(1.3, 1.9),
            stance_dist={"enthusiast": 0.1, "neutral": 0.3, "skeptic": 0.6},
        ),
    ],
)


_ECOMMERCE_SHOPPERS = Cohort(
    name="ecommerce_shoppers",
    description="Five buying mindsets common on PDP / landing pages.",
    segments=[
        SegmentArchetype(
            label="bargain hunter",
            description="Coupon-driven; discount-shopper, abandons full-price carts.",
            mbti_pool=["ISTJ", "ESFJ"],
            country_pool=["US", "UK", "BR", "IN"],
            profession_pool=["parent", "student", "office worker", "retiree"],
            interest_topics=["deals", "coupons", "discounts", "sales", "value"],
            sentiment_bias_range=(-0.2, 0.4),
            influence_weight_range=(0.6, 1.0),
            stance_dist={"enthusiast": 0.3, "neutral": 0.4, "skeptic": 0.3},
        ),
        SegmentArchetype(
            label="luxury seeker",
            description="Brand-pulled; willing to pay premium for proof and prestige.",
            mbti_pool=["ESTP", "ENTJ", "ENFJ"],
            country_pool=["US", "UK", "CN", "JP", "AE"],
            profession_pool=["executive", "founder", "doctor", "consultant"],
            interest_topics=["premium", "exclusivity", "craftsmanship", "brand", "status"],
            sentiment_bias_range=(0.0, 0.6),
            influence_weight_range=(1.2, 2.0),
            stance_dist={"enthusiast": 0.5, "neutral": 0.3, "skeptic": 0.2},
        ),
        SegmentArchetype(
            label="casual shopper",
            description="Browses on a whim; converts if friction is low.",
            mbti_pool=["ESFP", "ENFP", "ISFP"],
            country_pool=["US", "UK", "BR", "MX"],
            profession_pool=["service worker", "student", "freelancer", "office worker"],
            interest_topics=["browsing", "casual", "lifestyle", "new arrivals"],
            sentiment_bias_range=(-0.1, 0.5),
            influence_weight_range=(0.6, 1.1),
            stance_dist={"enthusiast": 0.3, "neutral": 0.5, "skeptic": 0.2},
        ),
        SegmentArchetype(
            label="repeat customer",
            description="Already loves the brand; needs reminder + new variant.",
            mbti_pool=["ESFJ", "ENFJ", "ISFJ"],
            country_pool=["US", "UK", "DE", "CN"],
            profession_pool=["parent", "professional", "creator", "manager"],
            interest_topics=["brand", "loyalty", "what's new", "exclusives"],
            sentiment_bias_range=(0.2, 0.7),
            influence_weight_range=(1.0, 1.5),
            stance_dist={"enthusiast": 0.6, "neutral": 0.3, "skeptic": 0.1},
        ),
        SegmentArchetype(
            label="skeptic",
            description="Evidence-driven; checks reviews and return policy.",
            mbti_pool=["INTJ", "INTP", "ISTJ"],
            country_pool=["US", "UK", "DE"],
            profession_pool=["analyst", "engineer", "researcher", "auditor"],
            interest_topics=["reviews", "comparisons", "return policy", "specs", "proof"],
            sentiment_bias_range=(-0.4, 0.2),
            influence_weight_range=(0.9, 1.4),
            stance_dist={"enthusiast": 0.15, "neutral": 0.35, "skeptic": 0.5},
        ),
    ],
)


_EMAIL_AUDIENCES = Cohort(
    name="email_audiences",
    description="Four email-audience temperatures across cold-email & lifecycle.",
    segments=[
        SegmentArchetype(
            label="cold prospect",
            description="Never heard of the company; ignores 95% of outreach.",
            mbti_pool=["INTJ", "INTP", "ISTJ"],
            country_pool=["US", "UK", "DE", "CA"],
            profession_pool=["VP", "director", "manager", "founder"],
            interest_topics=["scarcity", "specific value", "no fluff", "credibility"],
            sentiment_bias_range=(-0.6, 0.0),
            influence_weight_range=(0.6, 1.2),
            stance_dist={"enthusiast": 0.05, "neutral": 0.35, "skeptic": 0.6},
        ),
        SegmentArchetype(
            label="warm lead",
            description="Filled a form or downloaded something; semi-engaged.",
            mbti_pool=["ENFJ", "ENFP", "INFJ", "ENTJ"],
            country_pool=["US", "UK", "AU", "DE"],
            profession_pool=["manager", "director", "engineer", "founder"],
            interest_topics=["use cases", "demos", "proof", "next step"],
            sentiment_bias_range=(-0.1, 0.4),
            influence_weight_range=(1.0, 1.4),
            stance_dist={"enthusiast": 0.4, "neutral": 0.4, "skeptic": 0.2},
        ),
        SegmentArchetype(
            label="existing customer",
            description="Uses the product; wants new features and minimal noise.",
            mbti_pool=["ENFJ", "ESFJ", "ENFP"],
            country_pool=["US", "UK", "DE", "BR"],
            profession_pool=["manager", "engineer", "creator", "operator"],
            interest_topics=["new features", "upgrades", "tips", "community"],
            sentiment_bias_range=(0.1, 0.6),
            influence_weight_range=(1.0, 1.5),
            stance_dist={"enthusiast": 0.55, "neutral": 0.35, "skeptic": 0.1},
        ),
        SegmentArchetype(
            label="churned",
            description="Cancelled or lapsed; reactivation candidate, easily annoyed.",
            mbti_pool=["INTJ", "ISTJ", "ENTJ"],
            country_pool=["US", "UK", "DE"],
            profession_pool=["former customer", "manager", "founder"],
            interest_topics=["what changed", "win-back offer", "no spam", "minimal effort"],
            sentiment_bias_range=(-0.5, 0.1),
            influence_weight_range=(0.7, 1.2),
            stance_dist={"enthusiast": 0.1, "neutral": 0.3, "skeptic": 0.6},
        ),
    ],
)


_B2B_BUYERS = Cohort(
    name="b2b_buyers",
    description="B2B sales-cycle archetypes: champion, decision-maker, blocker, influencer.",
    segments=[
        SegmentArchetype(
            label="champion",
            description="Internal advocate; wants the deal to succeed.",
            mbti_pool=["ENFJ", "ENTJ", "ENFP"],
            country_pool=["US", "UK", "DE", "SG"],
            profession_pool=["manager", "senior engineer", "team lead"],
            interest_topics=["use cases", "value prop", "rollout plan", "ROI"],
            sentiment_bias_range=(0.2, 0.7),
            influence_weight_range=(1.2, 1.7),
            stance_dist={"enthusiast": 0.65, "neutral": 0.3, "skeptic": 0.05},
        ),
        SegmentArchetype(
            label="decision-maker",
            description="VP/exec who signs the contract; cares about strategic fit.",
            mbti_pool=["ENTJ", "INTJ", "ESTJ"],
            country_pool=["US", "UK", "DE"],
            profession_pool=["VP", "CTO", "CFO", "Director"],
            interest_topics=["ROI", "risk", "vendor lock-in", "TCO", "strategic alignment"],
            sentiment_bias_range=(-0.2, 0.4),
            influence_weight_range=(1.8, 2.5),
            stance_dist={"enthusiast": 0.25, "neutral": 0.4, "skeptic": 0.35},
        ),
        SegmentArchetype(
            label="blocker",
            description="Procurement / security / legal — looking for reasons to say no.",
            mbti_pool=["ISTJ", "INTJ"],
            country_pool=["US", "UK", "DE", "FR"],
            profession_pool=["procurement", "legal counsel", "security lead", "auditor"],
            interest_topics=["compliance", "security", "contracts", "SLAs", "exit clauses"],
            sentiment_bias_range=(-0.6, 0.1),
            influence_weight_range=(1.0, 1.5),
            stance_dist={"enthusiast": 0.05, "neutral": 0.25, "skeptic": 0.7},
        ),
        SegmentArchetype(
            label="influencer",
            description="End-user or peer team that affects the choice indirectly.",
            mbti_pool=["INFP", "INTP", "ENFP", "ISTP"],
            country_pool=["US", "UK", "IN", "DE"],
            profession_pool=["engineer", "analyst", "designer", "operator"],
            interest_topics=["daily workflow", "UX", "integration", "API quality"],
            sentiment_bias_range=(-0.1, 0.5),
            influence_weight_range=(0.8, 1.3),
            stance_dist={"enthusiast": 0.35, "neutral": 0.45, "skeptic": 0.2},
        ),
    ],
)


_PRD_READERS = Cohort(
    name="prd_readers",
    description="Internal readers of a PRD doc: eng lead, qa, peer PM, new hire.",
    segments=[
        SegmentArchetype(
            label="eng lead",
            description="Reads PRD to estimate scope, finds gaps.",
            mbti_pool=["INTJ", "INTP", "ENTJ"],
            country_pool=["US", "UK", "DE"],
            profession_pool=["tech lead", "engineering manager", "staff engineer"],
            interest_topics=["scope", "edge cases", "dependencies", "perf", "feasibility"],
            sentiment_bias_range=(-0.3, 0.3),
            influence_weight_range=(1.3, 1.8),
            stance_dist={"enthusiast": 0.2, "neutral": 0.4, "skeptic": 0.4},
        ),
        SegmentArchetype(
            label="qa",
            description="Reads PRD to design test cases; hunts ambiguity.",
            mbti_pool=["ISTJ", "INTJ"],
            country_pool=["US", "UK", "IN", "DE"],
            profession_pool=["QA engineer", "test lead", "automation engineer"],
            interest_topics=["acceptance criteria", "edge cases", "test data", "negative paths"],
            sentiment_bias_range=(-0.4, 0.2),
            influence_weight_range=(0.9, 1.4),
            stance_dist={"enthusiast": 0.15, "neutral": 0.35, "skeptic": 0.5},
        ),
        SegmentArchetype(
            label="peer PM",
            description="Reads to align with their own roadmap; spots conflicts.",
            mbti_pool=["ENTJ", "ENFJ", "INTJ"],
            country_pool=["US", "UK", "DE", "IN"],
            profession_pool=["product manager", "senior PM", "PMM"],
            interest_topics=["user story clarity", "metrics", "GTM", "dependencies"],
            sentiment_bias_range=(-0.1, 0.4),
            influence_weight_range=(1.0, 1.5),
            stance_dist={"enthusiast": 0.3, "neutral": 0.45, "skeptic": 0.25},
        ),
        SegmentArchetype(
            label="new hire",
            description="Reads to learn the system; surfaces hidden assumptions.",
            mbti_pool=["INFP", "ENFP", "INTP"],
            country_pool=["US", "UK", "IN", "BR"],
            profession_pool=["junior engineer", "intern", "new PM"],
            interest_topics=["context", "glossary", "background", "history"],
            sentiment_bias_range=(0.0, 0.5),
            influence_weight_range=(0.6, 1.0),
            stance_dist={"enthusiast": 0.4, "neutral": 0.45, "skeptic": 0.15},
        ),
    ],
)


COHORTS: dict[str, Cohort] = {
    c.name: c for c in [
        _AD_SEGMENTS, _SOCIAL_SEGMENTS, _US_SWING_VOTERS,
        _DEVELOPER_PERSONAS, _ECOMMERCE_SHOPPERS, _EMAIL_AUDIENCES,
        _B2B_BUYERS, _PRD_READERS,
    ]
}
