export type Locale = 'en' | 'ar'

export const translations = {
  en: {
    metaTitle: 'Rakkib - Agent-Driven Homeserver Setup',
    metaDescription: 'Rakkib turns a fresh machine into a self-hosted server stack with one guided install command.',
    brandLabel: 'Rakkib home',
    heroTitle: 'Your own server, installed by an AI agent.',
    heroText:
      'Rakkib transforms a fresh machine into a polished self-hosted stack for apps, data, automation, photos, and secure access.',
    copy: 'Copy',
    copied: 'Copied!',
    installNote:
      'One command. Guided setup. Rakkib finds your agent, prepares the machine, and walks you into a secure self-hosted stack.',
    sectionLabel: 'Installed services',
    servicesTitle: 'Core stack included. Optional tools when you want them.',
    optional: 'Optional',
    github: 'GitHub',
    services: {
      Caddy: 'Web server',
      Cloudflared: 'Secure tunnel',
      PostgreSQL: 'Database',
      NocoDB: 'No-code data UI',
      Authentik: 'SSO & auth proxy',
      Homepage: 'Service dashboard',
      'Uptime Kuma': 'Uptime monitoring',
      Dockge: 'Docker Compose UI',
      n8n: 'Automation',
      DBHub: 'Database MCP',
      Immich: 'Photo library',
      'transfer.sh': 'Public file sharing',
      OpenClaw: 'AI control UI',
      Hermes: 'AI agent dashboard',
    },
  },
  ar: {
    metaTitle: '«رَكِّب»  يضبّط سيرفرك بدون تعب وتحميل يدوي',
    metaDescription: '  ثبّت حزمة «ركّب» على سيرفرك المنزلي او جهازك الشخصي باستخدام الذكاء الاصطناعي',
    brandLabel: 'صفحة رَكِّب الرئيسية',
    heroTitle: '«ركب» يوفر لك جميع الادوات اللي تحتاجها على سيرفرك المنزلي',
    heroText:
      'واكب موجة أدوات الذكاء الاصطناعي.',
    copy: 'نسخ',
    copied: 'تم النسخ!',
    installNote:
      ' انسخ هذا الامر على جهازك وتفرج على «ركب» وهو يضبط جهازك وينقله للعصر الجديد',
    sectionLabel: 'الادوات/الخدمات المُثبّتة',
    servicesTitle: 'أخذنا من كل تصنيف الادوات الافضل والاسهل للاستخدام',
    optional: 'اختياري',
    github: 'Github ',
    services: {
      Caddy: 'تسمح باستخدام الدومنات الفرعيه لجميع ادواتك، مثل n8n.yourdomain.com',
      Cloudflared: 'كلاويد فير تغلق جميع المنافذ على سيرفرك الا منفذ واحد لكل الخدمات، آمن عالي وامكانية الدخول على سيرفرك من اي مكان',
      PostgreSQL: 'قاعدة بيانات لجميع التطبيقات تحت سقف واحد',
      NocoDB: 'واجهة لقاعدة البيانات',
      Authentik: 'بوابة نفاذ واحدة لكل تطبيقاتك بكلمة مرور رئيسية',
      Homepage: 'لوحة لاستعراض جميع التطبيقات',
      'Uptime Kuma': 'مراقبة اداء السيرفر وموارده',
      Dockge: 'واجهة Docker Compose',
      n8n: 'الاداه الشهيرة للأتمته',
      DBHub: 'MCP يستفيد منهاالوكيل الخاص فيك لسحب اي معلومه من اي تطبيق على سيرفرك',
      Immich: 'مكتبة صورك الخاصة',
      'transfer.sh': 'أداة رفع ملفات خاصه فيك  ',
      OpenClaw: 'سكرتيرك الاصطناعي الشهير والغني عن العريف   ',
      Hermes: 'مساعدك الشخصي ',
    },
  },
} as const

export type TranslationKey = keyof typeof translations.en
