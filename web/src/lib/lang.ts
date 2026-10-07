export type LangInfo = { code: string; name: string; dir: "ltr" | "rtl"; font: "" | "urdu" | "naskh"; placeholder: string;
  examples: string[] };

export const LANGS: LangInfo[] = [
  { code: "en", name: "English", dir: "ltr", font: "",
    placeholder: "Type or paste what you want the voice to say…",
    examples: ["Thanks for calling. Your new plan is active, and you'll see the change on your next bill.",
      "Once upon a time, in a village by the river, there lived a boy who could hear the rain before it fell.",
      "And he takes it on the half volley… it's high, it's long… and it's out of the ground!"] },
  { code: "ur", name: "Urdu", dir: "rtl", font: "urdu",
    placeholder: "یہاں وہ متن لکھیں جو آواز بولے گی… انگریزی الفاظ لاطینی رسم الخط میں لکھیں، جیسے package",
    examples: ["السلام علیکم sir، آپ کے نمبر کے لیے ایک خاص package دستیاب ہے جس میں unlimited انٹرنیٹ شامل ہے۔",
      "آج کی اہم خبروں میں، شہر میں بارش کے بعد موسم خوشگوار ہو گیا ہے۔ محکمہ موسمیات کے مطابق یہ سلسلہ کل تک جاری رہے گا۔",
      "کیا شاٹ ہے! گیند سیدھی باؤنڈری کے پار، اور اسٹیڈیم میں شور ہی شور!"] },
  { code: "ps", name: "Pashto", dir: "rtl", font: "naskh",
    placeholder: "دلته هغه متن ولیکئ چې غږ به یې ووايي…",
    examples: ["سلام ورور، ستاسو لپاره نن یو ځانګړی package شته چې unlimited انټرنیټ لري.",
      "زموږ په کلي کې یو زوړ سړی اوسېده چې هره ورځ به یې ماشومانو ته کیسې کولې."] },
  { code: "pa", name: "Punjabi (Shahmukhi)", dir: "rtl", font: "urdu",
    placeholder: "ایتھے اوہ لکھو جو آواز بولے گی…",
    examples: ["سلام جی، اج تہاڈے لئی اک نواں package آیا اے، جیہدے وچ unlimited انٹرنیٹ اے۔",
      "ساڈے پنڈ وچ اک بزرگ رہندے سن، جیہڑے ہر شام بچیاں نوں کہانیاں سناندے سن۔"] },
  { code: "sd", name: "Sindhi", dir: "rtl", font: "naskh",
    placeholder: "هتي اهو متن لکو جيڪو آواز ڳالهائيندو…",
    examples: ["سلام سائين، اڄ توهان لاءِ هڪ نئون package آهي جنهن ۾ unlimited انٽرنيٽ آهي.",
      "منهنجو نالو حسنين آهي ۽ مان اسلام آباد ۾ ڪم ڪندو آهيان."] },
];

export const langByCode = (c: string) => LANGS.find((l) => l.code === c) ?? LANGS[0];

const COLORS = ["#7c6cff", "#ff7ab6", "#3ccf91", "#f2b84b", "#6cc6ff", "#c39bff", "#ff8f6b", "#4fd1c5"];
export function avatarColor(id: string) {
  let h = 0;
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return COLORS[h % COLORS.length];
}
