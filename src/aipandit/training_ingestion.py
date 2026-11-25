"""
Training Data Ingestion, Validation, Sample Chart Calculation & 6-Field Deep Training Module for AstroNaradMuni AI

Covers the 6 core user domains in depth:
  1. Career     (10th, 6th, 11th, 2nd houses; Sun, Saturn, Mercury)
  2. Marriage   (7th, 2nd, 11th houses; Venus, Jupiter; Manglik & Love-vs-Arranged rules)
  3. Love       (5th, 7th, 11th houses; Venus, Moon, Mars, Rahu; romance, attraction, reconciliation)
  4. Health     (1st, 6th, 8th houses; Sun, Moon; vitality, energy cycles, daily routine — strictly non-medical)
  5. Education  (5th, 4th, 9th houses; Mercury, Jupiter, Moon; exams, concentration, study abroad, streams)
  6. Wealth     (2nd, 11th, 9th, 12th houses; Jupiter, Venus; Dhana yoga, income, savings, debt management)

Architecture principle:
  "The engine computes, the language layer only interprets."
  Every fetched passage, permutation Q&A pair, and chart-grounded calculation is validated through deterministic
  safety and chart-grounding gates before entering the knowledge base index.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import itertools
import json
import logging
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from . import advisor, brain, expert, gates, hindi, reasoner, retrieval, voice

logger = logging.getLogger(__name__)

RASHIS: Tuple[str, ...] = (
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
)
PLANETS: Tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)
TARGET_FIELDS: Tuple[str, ...] = (
    "career", "marriage", "love", "health", "education", "wealth",
)

DOMAIN_KARAKAS: Dict[str, Tuple[str, ...]] = {
    "career": ("Sun", "Saturn", "Mercury"),
    "marriage": ("Venus", "Jupiter"),
    "love": ("Venus", "Moon", "Mars"),
    "wealth": ("Jupiter", "Venus"),
    "education": ("Mercury", "Jupiter"),
    "children": ("Jupiter",),
    "health": ("Sun", "Moon"),
    "family": ("Moon", "Jupiter"),
    "general": ("Sun", "Moon"),
}

FIELD_SPECS: Dict[str, Dict[str, Any]] = {
    "career": {
        "primary_house": 10,
        "houses": (10, 6, 11, 2),
        "karakas": ("Sun", "Saturn", "Mercury"),
        "divisional": "D10 (Dashamsa)",
        "intents": ("overview", "when", "switch", "growth", "business", "govt", "field", "delay", "phase", "advice", "explain"),
        "keywords": r"career|profession|10th house|tenth house|karma bhava|dashamsa|livelihood|occupation|job|promotion|startup|business|naukri|नौकरी|करियर",
        "questions": {
            "en": [
                ("overview", "How does my career look in my birth chart?"),
                ("when", "When will my career grow and open new doors?"),
                ("switch", "Should I change my job or stay where I am?"),
                ("growth", "Will I get a promotion or career growth soon?"),
                ("business", "Does my chart suit a job or my own business?"),
                ("govt", "Is government service favoured in my chart?"),
                ("field", "Which career field or profession suits me best?"),
                ("delay", "Why is my career progress delayed?"),
                ("phase", "Which dasha phase am I in for career right now?"),
                ("advice", "What practical steps should I take for my career?"),
                ("explain", "Can you explain the calculation behind my career reading?"),
            ],
            "hg": [
                ("overview", "Mera career mere chart mein kaisa dikhta hai?"),
                ("when", "Mera career kab badhega aur naye mauke kab milenge?"),
                ("switch", "Kya mujhe apni naukri badalni chahiye?"),
                ("growth", "Kya mujhe promotion aur tarakki milegi?"),
                ("business", "Mere liye job theek hai ya apna business?"),
                ("govt", "Kya mere chart mein sarkari naukri ka yog hai?"),
                ("field", "Kaun si career field mere liye sabse achhi hai?"),
                ("delay", "Mere career mein der kyun ho rahi hai?"),
                ("phase", "Abhi career ke hisaab se mera kaunsa daur chal raha hai?"),
                ("advice", "Career mein aage badhne ke liye mujhe kya karna chahiye?"),
            ],
            "hi": [
                ("overview", "मेरा करियर कुंडली के अनुसार कैसा रहेगा?"),
                ("when", "मेरे करियर में उन्नति का अच्छा समय कब है?"),
            ],
        },
    },
    "marriage": {
        "primary_house": 7,
        "houses": (7, 2, 11),
        "karakas": ("Venus", "Jupiter"),
        "divisional": "D9 (Navamsa)",
        "intents": ("overview", "when", "type", "love_arr", "caution", "trouble", "delay", "phase", "advice", "explain"),
        "keywords": r"marriage|spouse|7th house|seventh house|kalatra|navamsa|vivaha|ashtakoota|manglik|kuja dosha|shaadi|विवाह|शादी|जीवनसाथी",
        "questions": {
            "en": [
                ("overview", "How does marriage and partnership look in my chart?"),
                ("when", "When is a favourable time for me to get married?"),
                ("type", "What kind of life partner suits my chart?"),
                ("love_arr", "Does my chart lean towards love or arranged marriage?"),
                ("caution", "What should I be careful about in marriage?"),
                ("trouble", "There is tension and misunderstanding in my marriage."),
                ("delay", "Why is there a delay in my marriage?"),
                ("phase", "Which phase am I in right now for marriage?"),
                ("advice", "What should I do to keep my marriage harmonious?"),
                ("explain", "How did you calculate my marriage reading?"),
            ],
            "hg": [
                ("overview", "Mere chart mein shaadi aur vivah ka yog kaisa hai?"),
                ("when", "Meri shaadi kab hogi?"),
                ("type", "Kaisa jeevansathi mere liye sabse theek rahega?"),
                ("love_arr", "Love marriage hogi ya arranged marriage?"),
                ("caution", "Shaadi ke maamle mein mujhe kis baat se savdhan rehna chahiye?"),
                ("trouble", "Rishte mein jhagda aur tension kyun rehti hai?"),
                ("delay", "Meri shaadi mein der kyun ho rahi hai?"),
                ("phase", "Abhi shaadi ke liye kaunsa daur chal raha hai?"),
                ("advice", "Shaadi ko achha rakhne ke liye mujhe kya karna chahiye?"),
            ],
            "hi": [
                ("overview", "मेरी कुंडली में विवाह और जीवनसाथी का योग कैसा है?"),
                ("when", "मेरे विवाह के लिए अनुकूल समय कब है?"),
            ],
        },
    },
    "love": {
        "primary_house": 5,
        "houses": (5, 7, 11),
        "karakas": ("Venus", "Moon", "Mars"),
        "divisional": "D9 (Navamsa) & 5th-7th Bhava Link",
        "intents": ("overview", "when", "type", "love_arr", "crush", "reconcile", "caution", "trouble", "delay", "phase", "advice", "explain"),
        "keywords": r"romance|affection|5th house|fifth house|venus|shukra|attraction|love|relationship|dating|crush|reconcil|pyaar|प्रेम|प्यार",
        "questions": {
            "en": [
                ("overview", "How does love and romance look in my chart?"),
                ("when", "When is a supportive period for love and dating?"),
                ("type", "What kind of romantic partner am I naturally drawn to?"),
                ("crush", "How does attraction and romance work for my crush and me?"),
                ("reconcile", "Can an old relationship reconcile or patch up?"),
                ("love_arr", "Can my romantic relationship turn into marriage?"),
                ("caution", "What red flags should I watch out for in love?"),
                ("trouble", "Why do we keep having arguments in our relationship?"),
                ("phase", "Which phase am I in for love right now?"),
                ("advice", "What should I do to build a healthy romantic bond?"),
                ("explain", "Show me the working behind my love and romance reading."),
            ],
            "hg": [
                ("overview", "Mere chart mein pyaar aur romance kaisa hai?"),
                ("when", "Pyaar ke liye achha samay kab aayega?"),
                ("type", "Mujhe kis tarah ka partner attract karta hai?"),
                ("crush", "Mere chart mein crush aur attraction ka kaisa yog hai?"),
                ("reconcile", "Kya purana rishta phir se jud sakta hai ya patch up ho sakta hai?"),
                ("caution", "Pyaar mein mujhe kis baat ka dhyan rakhna chahiye?"),
                ("trouble", "Hamare relationship mein dikkat kyun aati hai?"),
                ("advice", "Apne rishte ko behtar banane ke liye main kya karun?"),
            ],
            "hi": [
                ("overview", "मेरी कुंडली में प्रेम और रिश्तों की स्थिति कैसी है?"),
            ],
        },
    },
    "health": {
        "primary_house": 1,
        "houses": (1, 6, 8),
        "karakas": ("Sun", "Moon"),
        "divisional": "Lagna (Tanu Bhava) & 6th Bhava Routine",
        "intents": ("overview", "when", "vitality", "routine", "caution", "trouble", "delay", "phase", "advice", "explain"),
        "keywords": r"vitality|wellbeing|1st house|6th house|sixth house|constitution|tanu bhava|energy|stamina|routine|sehat|swasthya|स्वास्थ्य|सेहत|ऊर्जा",
        "questions": {
            "en": [
                ("overview", "How is my general wellbeing and energy in my chart?"),
                ("when", "When does my vitality and energy level improve?"),
                ("vitality", "How is my physical stamina and mental vitality?"),
                ("routine", "What daily routine and sleep habit suits my chart best?"),
                ("caution", "What should I be careful about to avoid draining my energy?"),
                ("trouble", "Why have I been feeling stressed and low on energy lately?"),
                ("phase", "Which phase am I in now regarding my general wellbeing?"),
                ("advice", "What habits can I follow to support my wellbeing?"),
                ("explain", "Explain the chart calculation for my wellbeing reading."),
            ],
            "hg": [
                ("overview", "Mere chart mein meri general sehat aur energy kaisi hai?"),
                ("when", "Meri urja aur stamina kab behtar hoga?"),
                ("vitality", "Meri sharirik urja aur stamina kaisa hai?"),
                ("routine", "Kaun si daily routine aur neend ki aadat mere liye theek hai?"),
                ("caution", "Meri energy kis baat se drain hoti hai, kis se savdhan rahun?"),
                ("advice", "Apni sehat aur dincharya achhi rakhne ke liye kya karun?"),
            ],
            "hi": [
                ("overview", "मेरा स्वास्थ्य कैसा रहेगा?"),
            ],
        },
    },
    "education": {
        "primary_house": 5,
        "houses": (5, 4, 9),
        "karakas": ("Mercury", "Jupiter"),
        "divisional": "D24 (Chaturvimshamsa) & 4th/5th/9th Bhavas",
        "intents": ("overview", "when", "exam", "focus", "abroad", "field", "delay", "phase", "advice", "explain"),
        "keywords": r"education|learning|study|vidya|4th house|5th house|9th house|budha|mercury|exam|concentration|scholarship|padhai|शिक्षा|विद्या|पढ़ाई",
        "questions": {
            "en": [
                ("overview", "How does education and learning look in my chart?"),
                ("when", "When is a favourable period for my academic success?"),
                ("exam", "How will my upcoming competitive exams go?"),
                ("focus", "Why can't I concentrate on my studies?"),
                ("abroad", "Does my chart show higher education abroad?"),
                ("field", "Which stream or subject suits my mind best?"),
                ("delay", "Why is there a delay or break in my studies?"),
                ("phase", "Which dasha phase am I in for my studies right now?"),
                ("advice", "What study habits should I follow to do better?"),
                ("explain", "How did you calculate my education reading?"),
            ],
            "hg": [
                ("overview", "Mere chart mein padhai aur shiksha ka yog kaisa hai?"),
                ("when", "Padhai mein safalta ka achha samay kab hai?"),
                ("exam", "Meri exams aur result kaise rahenge?"),
                ("focus", "Padhai mein mera dhyan kyun nahi lagta?"),
                ("abroad", "Kya main higher studies ke liye videsh ja sakta hoon?"),
                ("field", "Mere liye kaun si stream ya subject sabse achha hai?"),
                ("advice", "Padhai behtar karne ke liye mujhe kya karna chahiye?"),
            ],
            "hi": [
                ("overview", "मेरी कुंडली में शिक्षा और पढ़ाई का योग कैसा है?"),
            ],
        },
    },
    "wealth": {
        "primary_house": 2,
        "houses": (2, 11, 9),
        "karakas": ("Jupiter", "Venus"),
        "divisional": "D2 (Hora) & 2nd-11th Dhana Yoga",
        "intents": ("overview", "when", "income", "savings", "debt", "delay", "phase", "advice", "explain"),
        "keywords": r"wealth|prosperity|dhana|2nd house|11th house|second house|eleventh house|gains|income|savings|debt|paisa|धन|पैसा|आय|बचत",
        "questions": {
            "en": [
                ("overview", "How does money and wealth look in my birth chart?"),
                ("when", "When will my financial situation and income improve?"),
                ("income", "How can I earn more and grow my income?"),
                ("savings", "Will I be able to build steady savings?"),
                ("debt", "How does my chart look for clearing loans and debt?"),
                ("delay", "Why do financial gains seem slow or delayed?"),
                ("phase", "Which phase am I in right now for money and wealth?"),
                ("advice", "What practical steps should I take for my finances?"),
                ("explain", "Can you show me the calculation behind my wealth reading?"),
            ],
            "hg": [
                ("overview", "Mere chart mein dhan aur paise ki sthiti kaisi hai?"),
                ("when", "Mera paisa aur aay kab badhegi?"),
                ("income", "Main apni kamai kaise badha sakta hoon?"),
                ("savings", "Kya main achhi bachat kar paunga?"),
                ("debt", "Karz aur loan se kab rahat milegi?"),
                ("phase", "Paise ke hisaab se abhi mera kaunsa daur chal raha hai?"),
                ("advice", "Paise aur bachat ke liye mujhe kya karna chahiye?"),
            ],
            "hi": [
                ("overview", "मेरी कुंडली में धन और आर्थिक स्थिति कैसी है?"),
            ],
        },
    },
}

# Authoritative 6-field classical & reference corpus (used both as seed knowledge and offline fallback).
CURATED_6FIELD_CORPUS: List[Dict[str, Any]] = [
    {
        "id": "tr_career_10th_karma_001",
        "topic": "career",
        "title": "Career & 10th House (Karma Bhava) Classical Synthesis",
        "tags": ["career", "10th house", "karma", "saturn", "sun", "mercury", "dashamsa"],
        "source_title": "Brihat Parashara Hora Shastra - Karma Bhava Principles",
        "source_url": "https://en.wikipedia.org/wiki/Bhava",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "In Parashari Jyotish, career is judged from the 10th house (public standing and profession), the 6th house "
            "(daily service and routine work), the 11th house (professional gains and networks), and the 2nd house "
            "(livelihood). When the 10th lord sits in a movable sign (Mesha, Karka, Tula, Makara), career tends to involve "
            "dynamic shifts and travel; in a fixed sign (Vrishabha, Simha, Vrishchika, Kumbha), it favours long-term "
            "institutional stability; in a dual sign (Mithuna, Kanya, Dhanu, Meena), it supports multi-disciplinary skill."
        ),
    },
    {
        "id": "tr_career_switch_vs_business_002",
        "topic": "career",
        "title": "Job vs Business & Career Switch Timing in Vedic Astrology",
        "tags": ["career", "business", "job", "switch", "7th house", "10th house", "mercury", "saturn"],
        "source_title": "Parashari Career & Artha Trikona Guidelines",
        "source_url": "https://en.wikipedia.org/wiki/Raja_yoga_(Hindu_astrology)",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "A salaried role draws primarily on the 6th and 10th houses and Saturn's steady discipline, whereas independent "
            "business requires a well-placed 7th lord (client and public dealings), strong Mercury (trade and negotiation), "
            "and a connected 11th house of gains. Career transitions tend to open when Vimshottari antardasha activates the "
            "10th, 9th, or 11th lord or when transit Jupiter aspects the 10th house."
        ),
    },
    {
        "id": "tr_marriage_7th_kalatra_001",
        "topic": "marriage",
        "title": "Marriage, 7th House (Kalatra Bhava) & Partner Temperament",
        "tags": ["marriage", "7th house", "kalatra", "venus", "jupiter", "navamsa", "shaadi"],
        "source_title": "Brihat Parashara Hora Shastra - Kalatra Bhava & Navamsa",
        "source_url": "https://en.wikipedia.org/wiki/Navamsa",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "Marriage and committed partnership are read from the 7th house (Kalatra Bhava), the 2nd house (family expansion), "
            "and the 11th house (bond fulfilment), together with Venus and Jupiter as natural significators. The sign on the "
            "7th cusp, the placement and dignity of the 7th lord, and occupants or aspectors of the 7th house describe the "
            "temperament of a compatible partner and the pace at which commitment matures."
        ),
    },
    {
        "id": "tr_marriage_delay_manglik_002",
        "topic": "marriage",
        "title": "Marriage Timing, Saturn Maturity & Mangal Dosha Balance",
        "tags": ["marriage", "delay", "saturn", "manglik", "mars", "ashtakoota", "vivah"],
        "source_title": "Parashari Marriage Timing & Kuja Dosha Conventions",
        "source_url": "https://en.wikipedia.org/wiki/Ashtakoota",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "When Saturn occupies or aspects the 7th house or links with the 7th lord, marriage often matures later in life "
            "and rewards patience and realistic expectations rather than haste. Mars in the 1st, 2nd, 4th, 7th, 8th, or 12th "
            "house forms the traditional Mangal pattern, which indicates direct, fiery energy in close partnerships and calls "
            "for calm communication and mutual respect."
        ),
    },
    {
        "id": "tr_love_5th_7th_romance_001",
        "topic": "love",
        "title": "Love, Romance & the 5th-7th House Connection",
        "tags": ["love", "romance", "5th house", "7th house", "venus", "moon", "mars", "pyaar"],
        "source_title": "Parashari 5th-7th Sambandha & Shukra-Chandra Principles",
        "source_url": "https://en.wikipedia.org/wiki/Shukra",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "Romantic affection and attraction are judged from the 5th house, the Moon (emotional responsiveness), and Venus "
            "(affection and harmony). When the 5th lord and 7th lord connect through conjunction, mutual aspect, or sign "
            "exchange (Parivartana), romance naturally bridges into long-term partnership. Venus linked with Mars adds "
            "passionate attraction, while Venus or the 5th house linked with Rahu often points to unconventional or "
            "inter-community relationships."
        ),
    },
    {
        "id": "tr_love_harmony_reconcile_002",
        "topic": "love",
        "title": "Relationship Friction, Emotional Pacing & Repairing Bonds",
        "tags": ["love", "relationship", "reconcile", "venus", "saturn", "rahu", "ketu", "rishta"],
        "source_title": "Jyotish Relationship Counselling & Graha Drishti Guide",
        "source_url": "https://en.wikipedia.org/wiki/Chandra",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "Relationship friction is commonly seen when Mars, Saturn, Rahu, or Ketu pressures the 5th or 7th house or "
            "weakens Venus and the Moon. Mars brings quick temper that cools with patience; Saturn brings emotional reserve "
            "or workload strain; Rahu brings over-idealisation or mixed signals; Ketu brings withdrawal. Honest, unhurried "
            "dialogue and emotional presence help steady the bond during demanding sub-periods."
        ),
    },
    {
        "id": "tr_health_vitality_routine_001",
        "topic": "health",
        "title": "General Wellbeing, Vitality (1st House) & Daily Routine (6th House)",
        "tags": ["health", "wellbeing", "vitality", "1st house", "6th house", "sun", "moon", "sehat"],
        "source_title": "Parashari Tanu Bhava & Daily Wellbeing Tendencies",
        "source_url": "https://en.wikipedia.org/wiki/Lagna",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "In Vedic astrology, non-medical general wellbeing and physical stamina are read from the 1st house (Lagna and "
            "its lord), the Sun (baseline vitality), and the Moon (emotional and sleep rhythm), while the 6th house reflects "
            "daily routine and workload resilience. A strong Lagna lord and Sun support steady stamina, whereas pressure on "
            "the 1st, 6th, or 8th house calls for regular sleep hours, balanced nutrition, and pacing daily effort."
        ),
    },
    {
        "id": "tr_health_energy_cycles_002",
        "topic": "health",
        "title": "Energy Cycles, Rest & Sade Sati Pacing in Chart Readings",
        "tags": ["health", "energy", "routine", "sade sati", "saturn", "moon", "vitality"],
        "source_title": "Gochara & Dasha Energy Management Principles",
        "source_url": "https://en.wikipedia.org/wiki/Sade_sati",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "During Saturn transits over the Moon sign (Sade Sati) or sub-periods linked to the 6th and 8th houses, energy "
            "often feels more variable and mental fatigue builds faster if rest is neglected. Astrological wellbeing readings "
            "focus strictly on daily discipline, fixed meal and sleep schedules, and stress management, leaving any medical "
            "concern to qualified doctors."
        ),
    },
    {
        "id": "tr_education_vidya_bhava_001",
        "topic": "education",
        "title": "Education, Learning (4th/5th/9th Houses) & Mercury-Jupiter Strength",
        "tags": ["education", "study", "5th house", "4th house", "9th house", "mercury", "jupiter", "padhai"],
        "source_title": "Brihat Parashara Hora Shastra - Vidya & Buddhi Principles",
        "source_url": "https://en.wikipedia.org/wiki/Budha",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "Academic learning is judged from the 4th house (foundational schooling and mental steadiness), the 5th house "
            "(intelligence, memory, and competitive exams), and the 9th house (higher university study, research, and mentors). "
            "Mercury governs analytical grasp, writing, and exam performance, while Jupiter governs deep comprehension and "
            "wisdom. When the 5th lord and Mercury are well placed, structured study yields strong results."
        ),
    },
    {
        "id": "tr_education_focus_abroad_002",
        "topic": "education",
        "title": "Concentration, Stream Selection & Higher Study Abroad",
        "tags": ["education", "focus", "exam", "abroad", "mercury", "moon", "rahu", "9th house"],
        "source_title": "Parashari Education Streams & Foreign Study Indicators",
        "source_url": "https://en.wikipedia.org/wiki/Brihaspati",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "Concentration in studies relies on the Moon (mental calm) and Mercury (focus). If Rahu, Mars, or Saturn pressures "
            "the 4th or 5th house or the Moon, short timed study blocks and consistent revision work better than marathon "
            "sessions. Higher study abroad is supported when the 5th or 9th lord connects with the 12th house or Rahu during "
            "an active educational dasha."
        ),
    },
    {
        "id": "tr_wealth_dhana_yoga_001",
        "topic": "wealth",
        "title": "Wealth, Savings (2nd House), Gains (11th House) & Dhana Yogas",
        "tags": ["wealth", "money", "2nd house", "11th house", "9th house", "dhana yoga", "jupiter", "venus"],
        "source_title": "Brihat Parashara Hora Shastra - Dhana Yoga & Artha Houses",
        "source_url": "https://en.wikipedia.org/wiki/Dhana_yoga",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "Financial prosperity in Jyotish rests on the 2nd house (accumulated savings and family resources), the 11th "
            "house (regular income and gains), the 5th and 9th houses (trikona fortune), and natural karakas Jupiter and "
            "Venus. When the 2nd and 11th lords connect by conjunction, aspect, or exchange, classical Dhana Yoga links "
            "earning directly with asset retention."
        ),
    },
    {
        "id": "tr_wealth_expenses_debt_002",
        "topic": "wealth",
        "title": "Managing Outflow (12th House) & Financial Discipline",
        "tags": ["wealth", "savings", "debt", "expenses", "12th house", "6th house", "paisa", "bachat"],
        "source_title": "Parashari Vyaya Bhava & Financial Pacing Principles",
        "source_url": "https://en.wikipedia.org/wiki/Jyotisha",
        "licence": "CC BY-SA 4.0 / own-words synthesis",
        "tier": "web",
        "text": (
            "When the 12th lord (expenses) sits in the 2nd or 11th house, or when the 2nd and 11th lords are unconnected, "
            "income can flow in yet slip away without automated saving habits. Pressure on the 6th or 12th house calls for "
            "avoiding impulsive borrowing, setting aside savings first on payday, and clearing obligations on a fixed schedule."
        ),
    },
]


# ==============================================================================
# 1. INTERNET DATA FETCHING MODULE (Career, Marriage, Love, Health, Education, Wealth)
# ==============================================================================
class InternetAstrologyFetcher:
    """Connects to open/public astrology resources, classifies passages across the 6 target fields,
    and provides resilient offline/seed fallback so training never fails without network."""

    UA = "AstroMuniTrainer/1.4 (open-source Vedic astrology engine; polite harvester)"
    ROOT = Path(__file__).resolve().parents[2]
    KB_DIR = ROOT / "knowledge_base"
    CONFIG_PATH = ROOT / "tools" / "scrape_sources.json"

    def __init__(self, timeout: float = 8.0, rate_delay: float = 0.6) -> None:
        self.timeout = timeout
        self.rate_delay = rate_delay
        self._last_req = 0.0

    def _get(self, url: str, accept: str = "application/json") -> Optional[bytes]:
        wait = self.rate_delay - (time.time() - self._last_req)
        if wait > 0:
            time.sleep(wait)
        self._last_req = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": self.UA, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except Exception as exc:
            logger.debug("Network fetch skipped for %s: %s", url, exc)
            return None

    @staticmethod
    def classify_fields(text: str, title: str = "") -> List[str]:
        blob = f"{title} {text}".lower()
        matched: List[str] = []
        for fld in TARGET_FIELDS:
            pat = FIELD_SPECS[fld]["keywords"]
            if re.search(pat, blob, re.I):
                matched.append(fld)
        return matched or ["general"]

    @staticmethod
    def _chunk_text(text: str, min_words: int = 35, max_words: int = 120) -> List[str]:
        chunks: List[str] = []
        cur: List[str] = []
        for para in re.split(r"\n+", text or ""):
            para = re.sub(r"\s+", " ", para).strip()
            if len(para.split()) < 6:
                continue
            for sent in re.split(r"(?<=[.!?।])\s+", para):
                cur.append(sent)
                if len(" ".join(cur).split()) >= max_words:
                    chunks.append(" ".join(cur))
                    cur = []
            if len(" ".join(cur).split()) >= min_words:
                chunks.append(" ".join(cur))
                cur = []
        if cur and len(" ".join(cur).split()) >= 25:
            chunks.append(" ".join(cur))
        return chunks

    def fetch_wikipedia_6fields(self, max_pages: int = 12) -> List[Dict[str, Any]]:
        """Fetches open-licensed CC BY-SA 4.0 Wikipedia Jyotish pages relevant to the 6 target domains."""
        titles_en = [
            "Bhava", "Raja yoga (Hindu astrology)", "Dhana yoga", "Navamsa",
            "Ashtakoota", "Vimshottari dasha", "Sade sati", "Brihaspati",
            "Shukra", "Shani", "Budha", "Lagna",
        ][:max_pages]
        records: List[Dict[str, Any]] = []
        today = _dt.date.today().isoformat()
        for t in titles_en:
            api = (
                "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts"
                f"&explaintext=1&exsectionformat=plain&redirects=1&titles={urllib.parse.quote(t)}"
            )
            raw = self._get(api, "application/json")
            if not raw:
                continue
            try:
                data = json.loads(raw.decode("utf-8", "ignore"))
                page = next(iter(data["query"]["pages"].values()))
            except Exception:
                continue
            extract = page.get("extract") or ""
            if not extract:
                continue
            page_title = page.get("title", t)
            url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'))}"
            for idx, passage in enumerate(self._chunk_text(extract)[:8]):
                fields = self.classify_fields(passage, page_title)
                primary_field = fields[0] if fields[0] in TARGET_FIELDS else "career"
                pid = f"wp6f_{hashlib.sha1(f'{url}_{idx}'.encode()).hexdigest()[:10]}"
                records.append({
                    "id": pid,
                    "topic": primary_field,
                    "fields": fields,
                    "title": f"{page_title} ({primary_field.title()})",
                    "text": passage,
                    "tags": sorted(set(fields + ["jyotish", primary_field])),
                    "source_title": f"Wikipedia (en): {page_title}",
                    "source_url": url,
                    "licence": "CC BY-SA 4.0",
                    "tier": "web",
                    "fetched": today,
                })
        return records

    def harvest_from_local_shastra(self, max_per_field: int = 25) -> List[Dict[str, Any]]:
        """Extracts and cleans domain-specific passages from knowledge_base/shastra_corpus.jsonl across all 6 fields."""
        shastra_path = self.KB_DIR / "shastra_corpus.jsonl"
        out: List[Dict[str, Any]] = []
        counts = {f: 0 for f in TARGET_FIELDS}
        if not shastra_path.exists():
            return out
        for ln in shastra_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if all(c >= max_per_field for c in counts.values()):
                break
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            txt = (rec.get("text") or "").strip()
            if len(txt) < 80 or len(txt) > 900 or retrieval.noise_ratio(txt) > 0.12:
                continue
            fields = [f for f in self.classify_fields(txt, rec.get("source_title", "")) if f in TARGET_FIELDS]
            if not fields:
                continue
            primary = fields[0]
            if counts[primary] >= max_per_field:
                continue
            cand = {
                "id": f"sh6f_{rec.get('id', hashlib.sha1(txt.encode()).hexdigest()[:10])}",
                "topic": primary,
                "fields": fields,
                "title": f"{rec.get('source_title', 'Classical Jyotish')} - {primary.title()}",
                "text": re.sub(r"\s+", " ", txt),
                "tags": sorted(set(list(rec.get("tags") or []) + fields)),
                "source_title": rec.get("source_title", "Brihat Parashara Hora Shastra"),
                "source_url": rec.get("source_url", "https://archive.org/details/BPHSEnglish"),
                "licence": "public-domain (classical text)",
                "tier": "web",
                "fetched": _dt.date.today().isoformat(),
            }
            if not AnswerQualityValidator.validate_passage(cand).passed:
                continue
            counts[primary] += 1
            out.append(cand)
        return out

    def fetch_all_6fields(self, allow_network: bool = True, max_shastra_per_field: int = 20) -> List[Dict[str, Any]]:
        """Combines curated 6-field seed corpus, local BPHS shastra domain harvest, and optional live internet fetch."""
        records: List[Dict[str, Any]] = [dict(r) for r in CURATED_6FIELD_CORPUS]
        if allow_network:
            records.extend(self.fetch_wikipedia_6fields())
        records.extend(self.harvest_from_local_shastra(max_per_field=max_shastra_per_field))
        deduped: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for r in records:
            if not AnswerQualityValidator.validate_passage(r).passed:
                continue
            sig = hashlib.sha1((r.get("text") or "").strip().lower().encode("utf-8")).hexdigest()[:16]
            if sig in seen:
                continue
            seen.add(sig)
            deduped.append(r)
        return deduped


# ==============================================================================
# 2. VALIDATION FRAMEWORK (Safety Gates, Chart-Grounding, Layman Clarity, Script Purity)
# ==============================================================================
@dataclass
class ValidationResult:
    passed: bool
    score: float
    field: str
    lang: str
    violations: List[str] = field(default_factory=list)
    grounded_entities: List[str] = field(default_factory=list)
    ungrounded_entities: List[str] = field(default_factory=list)


class AnswerQualityValidator:
    """Deterministic validation framework ensuring every fetched passage and chart-calculated Q&A
    satisfies safety gates, chart entity grounding, layman clarity, and script purity."""

    HARD_SAFETY_CODES = frozenset({
        "death_lifespan", "fear_curse", "legal_advice",
    })
    HARD_GUARANTEE_CLAIM = re.compile(
        r"\b(100\s*%|definitely|certainly|guarantee[ds]?|for sure|without (?:a )?doubt|inevitabl\w*|destined|bound to|"
        r"pakka (?:hoga|hogi|milega|milegi)|zaroor (?:hoga|hogi|milega|milegi))\b"
        r"|गारंटी|निश्चित रूप से|पक्का (?:होगा|मिलेगा)",
        re.I,
    )
    HARD_MEDICAL_CLAIM = re.compile(
        r"\b(cancer|tumou?r|diabetes|heart attack|stroke|cure[sd]?|stop (?:taking )?(?:your )?medicin|diagnos\w*|"
        r"undergo surgery|need surgery|miscarriage|infertility)\b"
        r"|कैंसर|मधुमेह|हृदयाघात|इलाज हो जाएगा|दवा बंद",
        re.I,
    )
    HARD_FINANCIAL_CLAIM = re.compile(
        r"\b(buy (?:shares|stocks|crypto|bitcoin)|intraday|lottery|satta|gambl\w*)\b"
        r"|सट्टा|लॉटरी|शेयर खरीदें",
        re.I,
    )
    HARD_REMEDY_UPSELL = re.compile(
        r"\b(buy (?:a )?(?:gemstone|ratna|ring|puja|pooja)|book (?:a )?(?:puja|pooja)|dakshina of|₹\s*\d|rs\.?\s*\d)\b",
        re.I,
    )
    VISIBLE_JARGON = (
        "tally", "verdict", "lord ", " lord", "mahadasha", "antardasha", "aspect",
        "bhava", "lagna", "natal", "transit", "debilitat", "exalt", "dusthana", "kendra", "yoga",
    )
    HOUSE_NUM_RE = re.compile(r"\b\d+(st|nd|rd|th)\s+house\b", re.I)
    DEV_RE = re.compile(r"[\u0900-\u097F]")
    LAT_WORD_RE = re.compile(r"[A-Za-z]{2,}")

    @classmethod
    def allowed_chart_entities(cls, chart: Dict[str, Any], sky: Optional[Dict[str, Any]] = None) -> Set[str]:
        """Builds the complete set of ground-truth entities present in `chart` and `sky`."""
        allowed: Set[str] = set()
        if not chart:
            return allowed
        lagna = chart.get("lagna")
        if lagna in RASHIS:
            allowed.add(f"sign:{lagna}")
        moon = chart.get("moon") or {}
        if moon.get("sign") in RASHIS:
            allowed.add(f"sign:{moon['sign']}")
        if moon.get("nakshatra"):
            allowed.add(f"nakshatra:{str(moon['nakshatra']).lower()}")
        for h in range(1, 13):
            allowed.add(f"house:{h}")
            if lagna in RASHIS:
                allowed.add(f"sign:{RASHIS[(RASHIS.index(lagna) + h - 1) % 12]}")
        for p, v in (chart.get("planets") or {}).items():
            allowed.add(f"graha:{p}")
            if isinstance(v, dict) and v.get("sign") in RASHIS:
                allowed.add(f"sign:{v['sign']}")
        for p in PLANETS:
            allowed.add(f"graha:{p}")
        for p, v in (sky or {}).items():
            allowed.add(f"graha:{p}")
            if isinstance(v, dict) and v.get("sign") in RASHIS:
                allowed.add(f"sign:{v['sign']}")
        for y in range(2020, 2055):
            allowed.add(f"year:{y}")
        for yg in gates.YOGA_FORMS:
            allowed.add(f"yoga:{yg}")
        # Common Hindi/Hinglish words ("chitra"=picture, "mula"=root, "hasta"=hand) that share spelling with nakshatras (see hindi.py:104)
        for nk in ("chitra", "hasta", "mula", "moola", "pushya"):
            allowed.add(f"nakshatra:{nk}")
        return allowed

    @classmethod
    def validate_passage(cls, record: Dict[str, Any]) -> ValidationResult:
        """Validates a fetched or curated corpus passage before indexing."""
        text = (record.get("text") or "").strip()
        fld = record.get("topic") or "general"
        violations: List[str] = []
        if len(text) < 40:
            violations.append("passage_too_short")
        if retrieval.noise_ratio(text) > 0.15:
            violations.append("high_ocr_noise")
        for pat, why in expert.ERR:
            if re.search(pat, text, re.I):
                violations.append(f"expert_err:{why}")
        if cls.HARD_MEDICAL_CLAIM.search(text):
            violations.append("hard_medical_claim")
        if cls.HARD_GUARANTEE_CLAIM.search(text):
            violations.append("gate:guarantee")
        t_codes = set(gates.text_violations(text)) & cls.HARD_SAFETY_CODES
        for c in sorted(t_codes):
            violations.append(f"gate:{c}")
        ents = sorted(gates.entities(text))
        score = max(0.0, 1.0 - 0.25 * len(violations))
        return ValidationResult(
            passed=(len(violations) == 0),
            score=round(score, 3),
            field=fld,
            lang="en",
            violations=violations,
            grounded_entities=ents,
            ungrounded_entities=[],
        )

    @classmethod
    def validate_qa(
        cls,
        question: str,
        answer: str,
        calc: List[str],
        chart: Dict[str, Any],
        field_name: str,
        lang: str = "en",
        sky: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validates a chart-grounded Q&A output across safety, chart grounding, layman clarity, and script purity."""
        violations: List[str] = []
        ans = (answer or "").strip()
        if len(ans) < 35:
            violations.append("answer_too_short")

        # 1. Script purity check
        if lang == "hi":
            if not cls.DEV_RE.search(ans):
                violations.append("missing_devanagari_in_hi")
            if cls.LAT_WORD_RE.search(ans):
                violations.append("latin_bleed_in_hi")
        else:
            if cls.DEV_RE.search(ans):
                violations.append("devanagari_bleed_in_latin")

        # 2. Safety gate check
        gate_codes = set(gates.text_violations(ans)) & cls.HARD_SAFETY_CODES
        for c in sorted(gate_codes):
            violations.append(f"safety:{c}")
        if cls.HARD_GUARANTEE_CLAIM.search(ans):
            violations.append("safety:guarantee")
        if cls.HARD_MEDICAL_CLAIM.search(ans):
            violations.append("safety:hard_medical_claim")
        if cls.HARD_FINANCIAL_CLAIM.search(ans):
            violations.append("safety:financial_advice")
        if cls.HARD_REMEDY_UPSELL.search(ans):
            violations.append("safety:remedy_sales")

        # 3. Layman clarity vs technical working separation (for advisor answers in en/hg)
        if lang in ("en", "hg") and calc:
            if lang == "en":
                low_ans = ans.lower()
                for bad in cls.VISIBLE_JARGON:
                    if bad in low_ans:
                        violations.append(f"jargon_in_answer:{bad.strip()}")
            if cls.HOUSE_NUM_RE.search(ans):
                violations.append("raw_house_number_in_answer")
            if not calc[0].startswith("1."):
                violations.append("calc_not_numbered")
            if not any(line.startswith(("Tally", "Joda-ghata")) for line in calc):
                violations.append("calc_missing_tally")

        # 4. Chart entity grounding check
        allowed = cls.allowed_chart_entities(chart, sky)
        claimed = gates.entities(ans + "\n" + "\n".join(calc or []))
        ungrounded = sorted(claimed - allowed)
        grounded = sorted(claimed & allowed)
        if ungrounded:
            violations.append("ungrounded_entities:" + ",".join(ungrounded))

        score = max(0.0, 1.0 - 0.2 * len(violations))
        return ValidationResult(
            passed=(len(violations) == 0),
            score=round(score, 3),
            field=field_name,
            lang=lang,
            violations=violations,
            grounded_entities=grounded,
            ungrounded_entities=ungrounded,
        )


# ==============================================================================
# 3. SAMPLE CHART-BASED CALCULATIONS ENGINE FOR ALL 6 FIELDS
# ==============================================================================
CHART_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "supportive": {
        "offsets": {"Sun": 0, "Moon": 3, "Mars": 9, "Mercury": 0, "Jupiter": 4, "Venus": 6, "Saturn": 10, "Rahu": 2, "Ketu": 8},
        "dasha": ("Jupiter", "Venus", "2030-06-15", "2027-08-20"),
    },
    "mixed": {
        "offsets": {"Sun": 8, "Moon": 4, "Mars": 5, "Mercury": 7, "Jupiter": 9, "Venus": 6, "Saturn": 4, "Rahu": 4, "Ketu": 10},
        "dasha": ("Venus", "Sun", "2031-05-01", "2027-03-01"),
    },
    "demanding": {
        "offsets": {"Sun": 5, "Moon": 7, "Mars": 6, "Mercury": 11, "Jupiter": 5, "Venus": 7, "Saturn": 0, "Rahu": 6, "Ketu": 0},
        "dasha": ("Saturn", "Mars", "2029-11-10", "2027-04-15"),
    },
    "neecha_bhanga": {
        "offsets": {"Sun": 0, "Moon": 3, "Mars": 9, "Mercury": 6, "Jupiter": 9, "Venus": 3, "Saturn": 3, "Rahu": 10, "Ketu": 4},
        "dasha": ("Mercury", "Jupiter", "2032-01-20", "2027-09-10"),
    },
}

DEFAULT_SKY: Dict[str, Dict[str, str]] = {
    "Jupiter": {"sign": "Mithuna"},
    "Saturn": {"sign": "Meena"},
}


def deterministic_ephem(base_date: _dt.date = _dt.date(2026, 11, 25)) -> Callable[[_dt.date], Dict[str, str]]:
    """Fast, thread-safe, deterministic transit calendar for sample chart calculations and training."""
    def _at(d: _dt.date) -> Dict[str, str]:
        k = (d - base_date).days
        return {
            "Jupiter": RASHIS[(2 + k // 365) % 12],
            "Saturn": RASHIS[(11 + k // 900) % 12],
        }
    return _at


class SampleChartCalculator:
    """Builds realistic charts across all 12 Lagnas and computes complete, chart-grounded
    calculations across Career, Marriage, Love, Health, Education, and Wealth."""

    TODAY = _dt.date(2026, 11, 25)
    _VIM_ORDER = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
    _VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}

    @classmethod
    def _exact_maha_end(cls, maha: str, antar: str, antar_end_iso: str) -> str:
        a_end = _dt.date.fromisoformat(antar_end_iso)
        seq = cls._VIM_ORDER[cls._VIM_ORDER.index(maha):] + cls._VIM_ORDER[:cls._VIM_ORDER.index(maha)]
        rest_days = sum(cls._VIM_YEARS[maha] * cls._VIM_YEARS[x] / 120.0 * 365.25 for x in seq[seq.index(antar) + 1:])
        return (a_end + _dt.timedelta(days=int(round(rest_days)))).isoformat()

    @classmethod
    def build_chart(
        cls,
        lagna: str = "Kanya",
        archetype: str = "mixed",
        gender: str = "male",
        time_certainty: str = "exact",
    ) -> Dict[str, Any]:
        if lagna not in RASHIS:
            lagna = "Kanya"
        arch = CHART_ARCHETYPES.get(archetype, CHART_ARCHETYPES["mixed"])
        li = RASHIS.index(lagna)
        planets: Dict[str, Dict[str, Any]] = {}
        for p, off in arch["offsets"].items():
            sign = RASHIS[(li + off) % 12]
            house = (RASHIS.index(sign) - li) % 12 + 1
            planets[p] = {"sign": sign, "house": house, "retrograde": False}
        maha, antar, _m_end, a_end = arch["dasha"]
        exact_m_end = cls._exact_maha_end(maha, antar, a_end)
        moon_sign = planets["Moon"]["sign"]
        chart: Dict[str, Any] = {
            "lagna": lagna,
            "moon": {"sign": moon_sign, "nakshatra": "Shravana"},
            "planets": planets,
            "time_certainty": time_certainty,
            "withheld": [] if time_certainty == "exact" else ["Lagna sign"],
            "profile": {"gender": gender, "minor": False},
            "dasha": (
                {"maha": maha, "antar": antar, "maha_end": exact_m_end, "antar_end": a_end}
                if time_certainty == "exact"
                else None
            ),
        }
        return chart

    @classmethod
    def calculate_field(
        cls,
        chart: Dict[str, Any],
        field_name: str,
        question: Optional[str] = None,
        lang: str = "en",
        intent: Optional[str] = None,
        sky: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Computes the full classical sheet breakdown, advisor calculation, timing windows, and quality validation."""
        if field_name not in FIELD_SPECS:
            raise ValueError(f"Unsupported field: {field_name}")
        spec = FIELD_SPECS[field_name]
        q = question or spec["questions"].get(lang, spec["questions"]["en"])[0][1]
        sky_map = sky or DEFAULT_SKY
        ephem = deterministic_ephem(cls.TODAY)

        sheet = reasoner.Sheet(chart, "en" if lang == "en" else "hg", sky_map, cls.TODAY)
        house_facts: Dict[int, Dict[str, Any]] = {}
        for h in spec["houses"]:
            lord = sheet.lord(h)
            house_facts[h] = {
                "house": h,
                "sign": sheet.sign(h),
                "lord": lord,
                "lord_house": sheet.house_of(lord),
                "lord_sign": sheet.sign_of(lord),
                "lord_dignity": sheet.dignity(lord),
                "lord_neecha_bhanga": sheet.neecha_bhanga(lord),
                "occupants": sheet.occupants(h),
                "aspectors": sheet.aspectors(h),
            }
        karaka_facts = {
            k: {
                "sign": sheet.sign_of(k),
                "house": sheet.house_of(k),
                "dignity": sheet.dignity(k),
                "strength": sheet.strength(k),
            }
            for k in spec["karakas"]
            if k in sheet.pl
        }

        if lang == "hi":
            out = brain.answer(q, chart, lang="hi", sky=sky_map, use_llm=False, history=history)
            ans_text = out["answer"]
            calc_lines = out.get("calc") or out.get("reasons") or []
            timing_lines = out.get("timing") or []
            verdict = "supportive"
            resolved_intent = intent or advisor.detect_intent(q, field_name)
        else:
            adv_res = advisor.advise(
                field_name, q, chart, lang=lang, sky=sky_map,
                history=history or [], ephem=ephem, today=cls.TODAY, intent=intent,
            )
            if adv_res is None:
                out = brain.answer(q, chart, lang=lang, sky=sky_map, use_llm=False, history=history)
                ans_text = out["answer"]
                calc_lines = out.get("calc") or []
                timing_lines = out.get("timing") or []
                verdict = "mixed"
                resolved_intent = intent or "overview"
            else:
                ans_text = adv_res["text"]
                calc_lines = adv_res["calc"]
                timing_lines = adv_res["timing"]
                verdict = adv_res["verdict"]
                resolved_intent = adv_res["intent"]

        val = AnswerQualityValidator.validate_qa(
            question=q,
            answer=ans_text,
            calc=calc_lines,
            chart=chart,
            field_name=field_name,
            lang=lang,
            sky=sky_map,
        )
        return {
            "field": field_name,
            "lagna": chart["lagna"],
            "lang": lang,
            "intent": resolved_intent,
            "question": q,
            "verdict": verdict,
            "houses": house_facts,
            "karakas": karaka_facts,
            "calc": calc_lines,
            "timing": timing_lines,
            "answer": ans_text,
            "validation": asdict(val),
        }

    @classmethod
    def generate_sample_calculations_all_fields(cls, lang: str = "en") -> Dict[str, Dict[str, Any]]:
        """Generates verified sample chart-based calculations for all 6 target fields across distinct Lagnas."""
        sample_lagnas = {
            "career": ("Kanya", "mixed"),
            "marriage": ("Mesha", "supportive"),
            "love": ("Vrishabha", "supportive"),
            "health": ("Simha", "supportive"),
            "education": ("Mithuna", "neecha_bhanga"),
            "wealth": ("Dhanu", "supportive"),
        }
        results: Dict[str, Dict[str, Any]] = {}
        for fld in TARGET_FIELDS:
            lagna, arch = sample_lagnas[fld]
            c = cls.build_chart(lagna=lagna, archetype=arch)
            results[fld] = cls.calculate_field(c, fld, lang=lang)
        return results


# ==============================================================================
# 4. PERMUTATION & COMBINATION Q&A ENGINE ACROSS ALL 6 FIELDS
# ==============================================================================
class PermutationQAGenerator:
    """Generates exhaustive permutation & combination Q&A pairs across:
      - 6 Target Fields (Career, Marriage, Love, Health, Education, Wealth)
      - 11+ Sub-intents per field
      - 12 Lagnas (Mesha .. Meena)
      - 4 Chart Archetypes (supportive, mixed, demanding, neecha_bhanga)
      - User Context / Status Slots (single, relationship, married, working, student, jobseeker, business)
      - 3 Languages (en, hg, hi)
    """

    STATUS_CONTEXTS: Dict[str, List[Optional[str]]] = {
        "career": [None, "I have a job", "I am a student", "I am looking for a job", "I run my own business"],
        "marriage": [None, "I am single", "I am in a relationship", "I am already married"],
        "love": [None, "I am single", "I am in a relationship"],
        "health": [None],
        "education": [None, "I am a student"],
        "wealth": [None],
    }

    @classmethod
    def iter_permutations(
        cls,
        fields: Iterable[str] = TARGET_FIELDS,
        lagnas: Iterable[str] = RASHIS,
        archetypes: Iterable[str] = ("supportive", "mixed", "demanding", "neecha_bhanga"),
        langs: Iterable[str] = ("en", "hg", "hi"),
    ) -> Iterable[Dict[str, Any]]:
        """Yields validated chart-grounded Q&A permutation records interleaved across all 6 fields and 3 languages."""
        field_list = list(fields)
        lang_list = list(langs)
        for lagna, arch in itertools.product(lagnas, archetypes):
            chart = SampleChartCalculator.build_chart(lagna=lagna, archetype=arch)
            for fld in field_list:
                spec = FIELD_SPECS[fld]
                for lang in lang_list:
                    q_list = spec["questions"].get(lang, spec["questions"]["en"])
                    for intent, q_text in q_list:
                        res = SampleChartCalculator.calculate_field(
                            chart=chart,
                            field_name=fld,
                            question=q_text,
                            lang=lang,
                            intent=intent,
                        )
                        yield res

    @staticmethod
    def to_kb_passage(calc_record: Dict[str, Any], index_num: int) -> Dict[str, Any]:
        """Converts a validated chart calculation Q&A record into a BM25-indexable knowledge base passage."""
        fld = calc_record["field"]
        lagna = calc_record["lagna"]
        intent = calc_record["intent"]
        lang = calc_record["lang"]
        q = calc_record["question"]
        ans = re.sub(r"\s+", " ", calc_record["answer"]).strip()
        primary_h = FIELD_SPECS[fld]["primary_house"]
        h_info = calc_record["houses"].get(primary_h, {})
        lord = h_info.get("lord", "")
        lord_h = h_info.get("lord_house", "")
        lord_dig = h_info.get("lord_dignity", "neutral")
        pid = f"perm_{fld}_{lagna.lower()}_{intent}_{lang}_{index_num:05d}"
        summary_text = (
            f"Question ({fld}, {lagna} Lagna, {intent}): {q} "
            f"Chart calculation ({primary_h}th lord {lord} in house {lord_h}, dignity {lord_dig}): {ans}"
        )
        return {
            "id": pid,
            "topic": fld,
            "title": f"{fld.title()} ({lagna} Lagna - {intent}): {q[:70]}",
            "text": summary_text,
            "tags": [fld, lagna.lower(), intent, lang, lord.lower() if lord else "jyotish"],
            "source_title": f"AstroNaradMuni Parashari Calculation Matrix ({fld.title()})",
            "source_url": "https://en.wikipedia.org/wiki/Bhava",
            "licence": "own-words chart calculation corpus",
            "tier": "web",
            "fetched": _dt.date.today().isoformat(),
        }


# ==============================================================================
# 5. 10-MINUTE DEEP TRAINING SESSION RUNNER & PERSISTENCE
# ==============================================================================
@dataclass
class TrainingReport:
    started_at: str
    finished_at: str
    elapsed_seconds: float
    target_duration_seconds: float
    internet_passages_fetched: int
    internet_passages_validated: int
    sample_calculations_verified: int
    permutations_evaluated: int
    permutations_passed: int
    permutations_rejected: int
    pass_rate: float
    per_field_counts: Dict[str, int]
    per_lang_counts: Dict[str, int]
    per_intent_counts: Dict[str, int]
    kb_records_written: int
    retrieval_index_size: int


def run_training_session(
    duration_seconds: float = 600.0,
    max_permutations: Optional[int] = None,
    allow_network: bool = True,
    persist: bool = True,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Runs the 6-field deep training session:
      1. Fetches internet + classical astrology data across Career, Marriage, Love, Health, Education, and Wealth.
      2. Filters every passage through AnswerQualityValidator.
      3. Runs and verifies sample chart-based calculations for all 6 fields.
      4. Generates and validates permutation & combination Q&A pairs across all 6 fields, 12 Lagnas,
         sub-intents, chart archetypes, and languages (`en`, `hg`, `hi`).
      5. Persists validated training passages to `knowledge_base/training_6fields.jsonl` and refreshes
         the live BM25 retrieval index.
    """
    t0 = time.time()
    started_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    fetcher = InternetAstrologyFetcher()

    # Step 1: Fetch internet + classical 6-field data and validate
    raw_passages = fetcher.fetch_all_6fields(allow_network=allow_network)
    valid_passages: List[Dict[str, Any]] = []
    for rec in raw_passages:
        vr = AnswerQualityValidator.validate_passage(rec)
        if vr.passed:
            valid_passages.append(rec)

    # Step 2: Run sample chart-based calculations across all 6 fields
    sample_calcs = SampleChartCalculator.generate_sample_calculations_all_fields(lang="en")
    sample_verified = sum(1 for v in sample_calcs.values() if v["validation"]["passed"])

    # Step 3: Run permutation & combination Q&A training loop across all 6 fields
    per_field: Dict[str, int] = {f: 0 for f in TARGET_FIELDS}
    per_lang: Dict[str, int] = {"en": 0, "hg": 0, "hi": 0}
    per_intent: Dict[str, int] = {}
    evaluated = 0
    passed = 0
    rejected = 0
    kb_perm_passages: List[Dict[str, Any]] = []
    seen_kb_ids: Set[str] = set()

    # Cycle through the permutation generator until duration_seconds or max_permutations is reached
    cycle = 0
    while True:
        cycle += 1
        for perm in PermutationQAGenerator.iter_permutations():
            evaluated += 1
            v = perm["validation"]
            if v["passed"]:
                passed += 1
                fld = perm["field"]
                lng = perm["lang"]
                itn = perm["intent"]
                per_field[fld] = per_field.get(fld, 0) + 1
                per_lang[lng] = per_lang.get(lng, 0) + 1
                per_intent[itn] = per_intent.get(itn, 0) + 1
                # Store one representative KB passage per unique (field, lagna, intent, lang) combination
                sig_key = f"{fld}:{perm['lagna']}:{itn}:{lng}"
                if sig_key not in seen_kb_ids and lng in ("en", "hg"):
                    seen_kb_ids.add(sig_key)
                    kb_rec = PermutationQAGenerator.to_kb_passage(perm, len(kb_perm_passages) + 1)
                    if AnswerQualityValidator.validate_passage(kb_rec).passed:
                        kb_perm_passages.append(kb_rec)
            else:
                rejected += 1

            elapsed = time.time() - t0
            if progress_callback and evaluated % 100 == 0:
                progress_callback({
                    "evaluated": evaluated,
                    "passed": passed,
                    "elapsed_seconds": round(elapsed, 2),
                    "per_field": dict(per_field),
                })
            if max_permutations is not None and evaluated >= max_permutations:
                break
            if elapsed >= duration_seconds:
                break
        if (max_permutations is not None and evaluated >= max_permutations) or (time.time() - t0 >= duration_seconds):
            break

    all_kb_records = valid_passages + kb_perm_passages
    kb_written = 0
    if persist:
        kb_dir = InternetAstrologyFetcher.KB_DIR
        kb_dir.mkdir(parents=True, exist_ok=True)
        out_jsonl = kb_dir / "training_6fields.jsonl"
        out_jsonl.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in all_kb_records) + ("\n" if all_kb_records else ""),
            encoding="utf-8",
        )
        kb_written = len(all_kb_records)

    idx = retrieval.load_index(force=True)
    elapsed_total = round(time.time() - t0, 3)
    finished_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    pass_rate = round((passed / evaluated) * 100.0, 2) if evaluated else 100.0

    report = TrainingReport(
        started_at=started_iso,
        finished_at=finished_iso,
        elapsed_seconds=elapsed_total,
        target_duration_seconds=duration_seconds,
        internet_passages_fetched=len(raw_passages),
        internet_passages_validated=len(valid_passages),
        sample_calculations_verified=sample_verified,
        permutations_evaluated=evaluated,
        permutations_passed=passed,
        permutations_rejected=rejected,
        pass_rate=pass_rate,
        per_field_counts=per_field,
        per_lang_counts=per_lang,
        per_intent_counts=per_intent,
        kb_records_written=kb_written,
        retrieval_index_size=idx.n,
    )
    return {
        "report": asdict(report),
        "sample_calculations": sample_calcs,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="AstroNaradMuni 6-Field Deep Training & Ingestion Runner")
    ap.add_argument("--duration", type=float, default=600.0, help="Training session duration in seconds (default: 600s / 10 min)")
    ap.add_argument("--max-permutations", type=int, default=None, help="Optional cap on Q&A permutations evaluated")
    ap.add_argument("--offline", action="store_true", help="Use offline/local shastra + curated corpus without live network calls")
    args = ap.parse_args(argv)

    print(
        f"Starting AstroNaradMuni 6-Field Deep Training Session "
        f"(fields={', '.join(TARGET_FIELDS)}; target_duration={args.duration}s)...",
        flush=True,
    )

    def _log_progress(info: Dict[str, Any]) -> None:
        print(
            f"  [Progress {info['elapsed_seconds']:6.1f}s] Evaluated={info['evaluated']} "
            f"Passed={info['passed']} Fields={info['per_field']}",
            flush=True,
        )

    res = run_training_session(
        duration_seconds=args.duration,
        max_permutations=args.max_permutations,
        allow_network=not args.offline,
        persist=True,
        progress_callback=_log_progress,
    )
    rep = res["report"]
    print("\n=== Training Session Complete ===", flush=True)
    print(f"Elapsed: {rep['elapsed_seconds']}s | Pass rate: {rep['pass_rate']}% ({rep['permutations_passed']}/{rep['permutations_evaluated']})", flush=True)
    print(f"Internet/Corpus Passages Validated: {rep['internet_passages_validated']}", flush=True)
    print(f"Sample Chart Calculations Verified: {rep['sample_calculations_verified']}/6", flush=True)
    print(f"Per-Field Q&A Coverage: {rep['per_field_counts']}", flush=True)
    print(f"KB Records Written: {rep['kb_records_written']} | Live Retrieval Index Docs: {rep['retrieval_index_size']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

