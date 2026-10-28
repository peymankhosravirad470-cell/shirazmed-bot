# -*- coding: utf-8 -*-
"""English (en) UI strings — translated from fa.py (v46)."""

MSG = {
    "welcome": (
        "🌟 Send one message, and we'll prepare everything.\n\n"
        "From doctors to hotels, from transfers to translators, from appointments to city tours — all in one place.\n\n"
        "No worries, no hidden costs 💙\n\n"
        "👇 Choose from the buttons below:"
    ),
    "welcome_text": "Or write your request:\ne.g. \"heart doctor\" or \"treatment package\"",
    "more": "Do you have another question? (Yes / No)",
    "go": "Please go ahead and write your question.",
    "thanks": "🙏 Thank you!\n\nIf you were satisfied with our services, please recommend us to your friends and acquaintances. 🌹",
    "thanks_fb": "Thank you for your feedback. 🙏",
    "retry": "Sorry, I couldn't answer just now. Please try again.",
    "text_only": "Please write your question as text.",

    "apt_ask": "📅 To book an appointment with this doctor, press 1.\n📞 For a direct call, press 2.",
    "apt_pick_title": "👨‍⚕️ Doctors above:",
    "apt_pick_footer": "\n📅 To book an appointment, enter the number of the doctor you want:",
    "apt_choose_office": "🏥 Please choose your preferred office:",
    "apt_choose_date": "📅 Please choose the appointment date (next 14 days):",
    "apt_choose_time": "⏰ Please choose the appointment time:",
    "apt_ask_national_id": "🆔 Please enter your 10-digit national ID:",
    "apt_invalid_national_id": "❌ Invalid national ID. Please enter a valid 10-digit national ID.",
    "apt_ask_insurance": "🏥 Do you have insurance?",
    "apt_choose_insurance": "🏥 Please choose your insurance:",
    "apt_choose_payment_type": "💰 Choose the payment method:\n\n1️⃣ Full doctor fee\n2️⃣ Insurance share (after deduction)",
    "apt_ask_priority": "⚡ Appointment priority:\n\n1️⃣ Normal\n2️⃣ Urgent (extra fee)",
    "apt_name": "👤 Please write your full name:",
    "apt_phone": "📞 Please write your phone number (e.g. 09123456789):",
    "apt_confirm_final": (
        "Should the request be submitted with this information? (Yes / No)\n\n"
        "👤 Name: {name}\n"
        "📞 Phone: {phone}\n"
        "🆔 National ID: {nid}\n"
        "👨‍⚕️ Doctor: {doctor}\n"
        "🏥 Office: {office}\n"
        "📅 Date: {date}\n"
        "⏰ Time: {time}\n"
        "🏥 Insurance: {insurance}\n"
        "💰 Amount: {amount}\n"
        "⚡ Priority: {priority}"
    ),
    "apt_submitted": (
        "✅ Your appointment request has been submitted!\n\n"
        "📋 Tracking code: {id}\n"
        "👨‍⚕️ Doctor: {doctor}\n\n"
        "⏳ We will call the office and arrange the earliest available appointment for you."
    ),
    "apt_cancelled": "❌ Appointment submission cancelled.",
    "apt_invalid": "Please press one of the numbers provided.\n\n🚪 To exit: menu",
    "apt_error": "❌ Unfortunately, there was a problem submitting the appointment.",
    "apt_my": "📋 Your appointments:",
    "apt_none": "You haven't booked any appointments yet.",
    "apt_confirm_yes_no": "Do you confirm? (Yes / No)",

    "apt_admin_new": (
        "📥 New appointment request\n\n"
        "📋 Code: {id}\n"
        "👤 Patient: {name}\n"
        "📞 Phone: {phone}\n"
        "🆔 National ID: {nid}\n"
        "👨‍⚕️ Doctor: {doctor}\n"
        "📞 Office phone: {dphone}\n"
        "🏥 Office: {office}\n"
        "📅 Date: {date}\n"
        "⏰ Time: {time}\n"
        "🏥 Insurance: {insurance}\n"
        "💰 Amount: {amount}\n"
        "⚡ Priority: {priority}\n\n"
        "⏳ Confirm:\n/confirm {id} 1405/09/20 10:30\n"
        "✅ Mark visit as done:\n/done {id}"
    ),
    "apt_patient_confirmed": (
        "🎉 Your appointment is confirmed!\n\n"
        "📋 Code: {id}\n"
        "👨‍⚕️ Doctor: {doctor}\n"
        "📅 Date: {date}\n"
        "⏰ Time: {time}\n"
        "📍 Address: {address}"
    ),
    "apt_done_admin_ok": "✅ Visit {id} marked as done. Patient feedback request sent.",
    "apt_done_admin_bad": "❌ Appointment {id} not found.",
    "apt_done_patient": "🎊 We hope your visit went well!\n\nPlease tell us how satisfied you were with our services:",

    "pt_created": "🎫 Your file has been created\n\n📋 File code: {code}\n\nWhenever you want to check our progress, write: file",
    "pt_title": "🎫 Your Health File\n━━━━━━━━━━━━━━━",
    "pt_code": "📋 File code: {code}",
    "pt_name": "👤 Name: {name}",
    "pt_progress": "\n🌟 Your path to treatment:",
    "pt_stage_done": "✅ {stage}",
    "pt_stage_wait": "⏳ {stage}",
    "pt_stages_request": "Your request was submitted",
    "pt_stages_doctor": "Doctor assigned",
    "pt_stages_date": "Appointment date finalized",
    "pt_stages_accommodation": "Accommodation arranged",
    "pt_stages_transport": "Transport arranged",
    "pt_stages_treatment": "Treatment completed",
    "pt_stages_followup": "Health follow-up",
    "pt_appointments": "\n📅 Your appointments:",
    "pt_apt_line_pending": "⏳ {id} — {doctor} — awaiting date confirmation",
    "pt_apt_line_confirmed": "✅ {id} — {doctor} — {date} at {time}",
    "pt_apt_line_done": "🎊 {id} — {doctor} — completed",
    "pt_not_found": "You don't have a file yet. With your first appointment, your file will be created 💙",

    "delete_ask": "⚠️ Are you sure? To confirm, type: yes delete",
    "delete_done": "✅ All your information has been deleted.",
    "delete_cancel": "Okay, your information remains untouched.",

    "rate_thanks_5": "🌟 Wow, 5 stars! We're so happy 💙\n\nIf you have a friend who needs a doctor, please recommend us. You'll earn a reward 🎁",
    "rate_thanks_4": "😊 Thank you for the 4-star rating!\n\nIf you have a friend who needs a doctor, recommend us 🎁",
    "rate_thanks_3": "🙏 Thank you for your feedback.\n\nWe'll try to do better next time 💙",
    "rate_thanks_low": "😔 We're sorry you weren't satisfied.\n\nPlease tell us what caused your dissatisfaction so we can improve:",
    "rate_thanks_low_admin": "❌ New dissatisfaction\n\n📋 Appointment: {id}\n⭐ Rating: {stars}\n👤 Patient: {name}\nChatID: {cid}\n\n💬 Feedback:\n{text}",
    "rate_feedback_thanks": "🙏 Thank you for your feedback.\n\nWe will definitely follow up 💙",

    "remind_apt_1d": "⏰ Appointment reminder\n\n📅 Tomorrow at {time}\n👨‍⚕️ {doctor}\n📍 {address}\n\nPlease arrive 15 minutes early. 💙",
    "remind_apt_2h": "⏰ Appointment reminder\n\n🕐 In 2 hours\n👨‍⚕️ {doctor}\n⏰ At {time}\n📍 {address}\n\nWe're waiting for you 🌷",
    "remind_med": "💊 Medication reminder\n\nIt's time to take {med}.\n\nYour health matters 💙",

    "taxi_title": "🚕 Request a Taxi\n\nTo get to your destination, open one of the apps below and enter the destination:",

    "hub_not_found": "❌ Information for this terminal is not available.",
    "insurance_title": "🏥 Supported Insurances\n\n👇 Choose your insurance:",
    "insurance_not_found": "❌ Information for this insurance is not available.",
    "translator_title": "🗣️ Companion Translator\n\nChoose source and target languages:",
    "translator_processing": "⏳ Translating...",
    "translator_result": "📝 Original text:\n{original}\n\n🌍 Translation:\n{translated}",
    "translator_error": "❌ Unfortunately, translation failed.\n\nPlease try again.",
    "translator_too_long": "❌ The voice message is longer than 1 minute.\n\nPlease send a shorter one.",
    "translator_active": "✅ Translator activated\n\nSend a voice message (max 1 minute).\n\nTo exit: menu",
    "translator_listen": "🔊 Listen on Google Translate",

    "charter_title": "📜 Shiraz Medical Ethical Charter",
    "charter_body": (
        "At Shiraz Medical, we are committed to:\n\n"
        "1. Respect and Human Dignity\n"
        "We treat every patient with full respect, regardless of nationality, language, religion, or financial ability.\n\n"
        "2. Full Price Transparency\n"
        "No hidden costs. Before every service, the exact and transparent price is announced.\n\n"
        "3. Confidentiality of Information\n"
        "Your medical and personal information is a trust with us and will not be shared with anyone without your permission.\n\n"
        "4. Freedom to Choose Your Doctor\n"
        "You have the right to freely choose your doctor, hospital, and medical center.\n\n"
        "5. Informed Consent\n"
        "Before any medical procedure, all aspects, risks, and benefits are explained to you.\n\n"
        "6. Follow-up and Responsibility\n"
        "We stay with you until the end of your treatment journey, even after you return to your country.\n\n"
        "7. Non-Discrimination\n"
        "No patient is denied our services due to nationality, gender, religion, or disability.\n\n"
        "8. Medical Honesty\n"
        "No unnecessary service is imposed on you. Only what is needed for your health is offered.\n\n"
        "9. Right to Complain\n"
        "You always have the right to complain, give feedback, and receive a response.\n\n"
        "10. Preservation of Human Dignity\n"
        "Your body, privacy, and beliefs are always respected.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💙 Shiraz Medical\n"
        "Your Health, Our Commitment"
    ),

    "deepseek_title": "🤖 DeepSeek Smart Assistant\n\nAsk any question: medical, translation, consultation, anything.\n\nFree and unlimited 🚀",

    "pay_creating": "⏳ Creating payment link...",
    "pay_link": (
        "💳 Your payment link is ready:\n\n"
        "📋 Payment code: {pid}\n"
        "💰 Amount: {amount} Toman\n"
        "📅 Appointment: {apt_id}\n\n"
        "👇 Tap the button below and complete your payment:"
    ),
    "pay_button": "💳 Pay {amount} Toman",
    "pay_pending": "⏳ Your payment is awaiting confirmation.\n\nAfter payment, enter the tracking code here or tap \"Check Payment\".",
    "pay_check_button": "🔄 Check Payment",
    "pay_success": "✅ Your payment was successful!\n\n📋 Bank tracking code: {ref}\n💳 Payment code: {pid}",
    "pay_failed": "❌ Payment failed.\n\nPlease try again or contact support.",
    "pay_not_found": "❌ No payment found with this code.",
    "pay_error": "❌ Error creating payment. Please try again later.",
    "pay_amount_mismatch": "❌ The paid amount does not match the appointment amount. The issue has been sent to support for review.",
    "pay_already_verified": "ℹ️ This payment was already verified and recorded.",
    "invoice_button": "📄 Get Official Invoice",
    "invoice_generating": "⏳ Generating invoice...",
    "invoice_caption": "📄 Official invoice for appointment {apt_id}\n\n💰 Amount: {amount}\n🆔 Tracking code: {ref}",

    "payment_full": "Full payment",
    "payment_insurance": "Insurance share",
    "priority_normal": "Normal",
    "priority_urgent": "Urgent",

    "price_unknown": "Unknown — will be announced after doctor's review",

    "admin_only": "⛔️ This command is for administrators only.",

    "help": "Bot guide:\n\n• Use /start to begin.\n• Use the Back button to return to the main menu.\n• Use the Change Language button to switch languages.\n\nSelect one of the main menu options to use our services.",
}

MSG_BTN = {
    "btn_docs": "👨‍⚕️ Medical",
    "btn_nonmed": "🏥 Non-medical",
    "btn_tourist": "🏛️ Tourism",
    "btn_para": "🏥 Paramedical",
    "btn_elder": "🏡 Nursing Home",
    "btn_pkg": "💎 Complete Package",
    "btn_file": "📋 File",
    "btn_apt": "📅 My Appointments",
    "btn_med": "💊 Medication Reminder",
    "btn_sos": "🚨 Emergency",
    "btn_invite": "🎁 Invite Friends",
    "btn_help": "🆘 Patient Rights",
    "btn_channel": "📢 Join Channel",

    "btn_taxi": "🚕 Request Taxi",
    "btn_snapp": "🚗 Snapp",
    "btn_tap30": "🚕 Tap30",

    "btn_hubs": "🚉 Terminals & Airport",
    "btn_back_hubs": "🔙 Back to Terminals List",

    "btn_insurance": "🏥 Supported Insurances",
    "btn_back_insurance": "🔙 Back to Insurances List",

    "btn_translator": "🗣️ Companion Translator",
    "btn_tr_fa_ar": "🇮🇷 Persian → 🇸🇦 Arabic",
    "btn_tr_ar_fa": "🇸🇦 Arabic → 🇮🇷 Persian",
    "btn_tr_fa_en": "🇮🇷 Persian → 🇬🇧 English",
    "btn_tr_en_fa": "🇬🇧 English → 🇮🇷 Persian",

    "btn_charter": "📜 Ethical Charter",
    "btn_deepseek": "🤖 DeepSeek AI",
    "btn_deepseek_go": "🚀 Go to DeepSeek",

    "btn_back": "🔙 Back",
    "btn_feedback": "💬 Feedback",
    "btn_change_lang": "🌐 Change Language",
    "btn_site": "🌐 Website Address",


    "btn_hospitals": "🏥 Hospitals",
    "btn_hotels": "🏨 Hotels",
    "btn_motels": "🛏️ Motels",
    "btn_houses": "🏠 Guest Houses",
    "btn_transport": "🚗 Transport",

    "btn_city": "🏛️ City Attractions",
    "btn_outside": "🏞️ Outside the City",

    "btn_physio": "🦴 Physiotherapy",
    "btn_lab": "🔬 Laboratory",
    "btn_radiology": "📷 Radiology",
    "btn_nursing": "👩‍⚕️ Nursing",
    "btn_injection": "💉 Injection",
    "btn_trad_med": "🌿 Traditional Medicine",
    "btn_occupational": "🧩 Occupational Therapy",
    "btn_speech": "🗣️ Speech Therapy",
    "btn_orthotics": "🦿 Prosthetics",

    "btn_elder_all": "🏡 All Nursing Homes",

    "btn_pkg_order": "💎 Order Package",

    "btn_book": "📅 Book Appointment",
    "btn_companion": "🤝 Register Companion",
    "btn_survey": "📝 Survey & Feedback",
    "btn_call": "📞 Call",

    "medical": "👨‍⚕️ Medical",
    "non_medical": "🏥 Non-medical",
    "tourism": "🏛️ Tourism",
    "paramedical": "🏥 Paramedical",
    "elderly": "🏡 Nursing Home",
    "package": "💎 Complete Package",
    "hubs": "🚉 Terminals & Airport",
    "taxi": "🚕 Request Taxi",
    "insurance": "🏥 Supported Insurances",
    "translator": "🗣️ Companion Translator",
    "charter": "📜 Ethical Charter",
    "deepseek": "🤖 DeepSeek AI",
    "file": "📋 File",
    "appointments": "📅 My Appointments",
    "medication": "💊 Medication Reminder",
    "emergency": "🚨 Emergency",
    "channel": "📢 Join Channel",
    "invite": "🎁 Invite Friends",
    "rights": "⚖️ Patient Rights",
}

INSURANCE_FIELD_LABELS = {
    "type": "Insurance type",
    "coverage_gp_visit": "GP visit",
    "coverage_specialist": "Specialist visit",
    "coverage_subspecialist": "Sub-specialist visit",
    "coverage_hospitalization": "Hospitalization",
    "coverage_surgery": "Surgery",
    "coverage_medication_opd": "Outpatient medication",
    "coverage_medication_ipd": "Inpatient medication",
    "coverage_lab": "Laboratory",
    "coverage_radiology": "Radiology",
    "coverage_mri_ct": "MRI and CT scan",
    "coverage_sonography": "Sonography",
    "coverage_physiotherapy": "Physiotherapy",
    "coverage_occupational": "Occupational therapy",
    "coverage_speech": "Speech therapy",
    "coverage_dentistry_restorative": "Restorative dentistry",
    "coverage_dentistry_cosmetic": "Cosmetic dentistry",
    "coverage_vision": "Glasses and vision",
    "coverage_natural_birth": "Natural birth",
    "coverage_csection": "Cesarean section",
    "coverage_dialysis": "Dialysis",
    "coverage_chemotherapy": "Chemotherapy",
    "coverage_radiotherapy": "Radiotherapy",
    "coverage_psychiatry": "Psychiatry",
    "coverage_ambulance": "Ambulance",
    "annual_cap": "Annual cap",
    "per_admission_cap": "Per-admission cap",
    "deductible_visit": "Visit deductible",
    "deductible_hospital": "Hospital deductible",
    "deductible_medication": "Medication deductible",
    "annual_medication_cap": "Annual medication cap",
    "waiting_period": "Waiting period",
    "special_diseases": "Special diseases covered",
    "exclusions": "Exclusions",
    "age_limit": "Age limit for coverage",
    "foreign_patient_coverage": "Foreign patient coverage",
    "installment_payment": "Installment payment available",
    "required_documents": "Required documents",
    "usage_summary": "How to use",
    "contracted_centers": "Contracted centers",
    "claim_processing_time": "Claim processing time",
    "complaint_process": "Complaint process",
    "main_phone": "Main phone",
    "support_phone_24h": "24/7 support",
    "website": "Website",
    "mobile_app": "Mobile app",
    "email": "Email",
    "shiraz_offices": "Shiraz offices",
    "total_insured": "Total insured",
    "population_coverage_pct": "Population coverage (%)",
    "total_contracted_centers": "Number of contracted centers",
    "total_contracted_doctors": "Number of contracted doctors",
}

FIELD_NAMES = {
    "name": "Name", "address": "Address", "phone": "Phone", "specialty": "Specialty",
    "office_address": "Office address", "working_hours": "Working hours",
    "price_range_toman": "Price", "price_range": "Price",
    "patient_satisfaction_score": "Rating", "rating": "Rating",
    "reviews_summary": "Traveler reviews", "surgeries_done_at": "Hospitals",
    "category": "Category", "star_rating": "Stars", "quality_grade": "Quality",
    "district": "District", "amenities": "Amenities", "distance_to_hospitals": "Distance to hospitals",
    "has_translator": "Translator", "languages_spoken": "Languages",
    "description": "Description", "services": "Services", "type": "Type",
    "has_home_service": "Home service", "capacity": "Capacity",
}