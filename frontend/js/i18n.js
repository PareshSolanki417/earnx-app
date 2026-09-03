// ==========================================================================
// EarnX Internationalization (i18n) Engine
// Supports English, Hindi (हिन्दी), and Gujarati (ગુજરાતી)
// ==========================================================================

const i18n = {
  currentLang: localStorage.getItem('earnx_lang') || 'en',

  translations: {
    en: {
      available_balance: "Available Balance",
      coins: "Coins",
      wallet: "Wallet",
      withdraw: "Withdraw",
      watch_and_earn: "Watch & Earn",
      watch_subtitle: "Watch verified sponsor video to receive instant coins",
      recommended: "⚡ Instant Reward",
      daily_progress: "Daily Goal",
      progress_tip: "Complete daily activities to qualify for higher tiers",
      daily_bonus: "Daily Bonus",
      tasks: "Daily Tasks",
      referral: "Refer & Earn",
      home: "Home",
      watch: "Watch",
      profile: "Profile",
    },
    hi: {
      available_balance: "उपलब्ध बैलेंस",
      coins: "सिक्के",
      wallet: "वॉलेट",
      withdraw: "पैसे निकालें",
      watch_and_earn: "देखें और कमाएं",
      watch_subtitle: "सत्यापित स्पॉन्सर वीडियो देखें और तुरंत सिक्के पाएं",
      recommended: "⚡ त्वरित इनाम",
      daily_progress: "दैनिक लक्ष्य",
      progress_tip: "उच्च स्तर के लिए दैनिक कार्य पूरे करें",
      daily_bonus: "दैनिक बोनस",
      tasks: "दैनिक कार्य",
      referral: "दोस्त जोड़ें और कमाएं",
      home: "होम",
      watch: "वीडियो",
      profile: "प्रोफ़ाइल",
    },
    gu: {
      available_balance: "ઉપલબ્ધ બેલેન્સ",
      coins: "સિક્કા (Coins)",
      wallet: "વોલેટ",
      withdraw: "ઉપાડો (Withdraw)",
      watch_and_earn: "જુઓ અને કમાઓ",
      watch_subtitle: "સ્પોન્સર વિડિયો જુઓ અને તરત સિક્કા મેળવો",
      recommended: "⚡ ત્વરિત ઈનામ",
      daily_progress: "દૈનિક લક્ષ્ય",
      progress_tip: "વધુ ઈનામો મેળવવા દૈનિક પ્રવૃત્તિઓ પૂર્ણ કરો",
      daily_bonus: "દૈનિક બોનસ",
      tasks: "દૈનિક કાર્યો",
      referral: "મિત્રોને જોડો અને કમાઓ",
      home: "હોમ",
      watch: "વિડિયો",
      profile: "પ્રોફાઈલ",
    }
  },

  setLanguage(lang) {
    if (!this.translations[lang]) return;
    this.currentLang = lang;
    localStorage.setItem('earnx_lang', lang);
    this.applyTranslations();
  },

  t(key) {
    const dict = this.translations[this.currentLang] || this.translations.en;
    return dict[key] || key;
  },

  applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = this.t(key);
    });
    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.value = this.currentLang;
  }
};
