import fs from "node:fs";
import path from "node:path";

export type DevotionalEntry = {
  id: string;
  source: {
    reference: {
      zh: string;
      en: string;
    };
  };
  scripture: {
    zh: string;
    en: string;
  };
  reflection: {
    zh: {
      title: string;
      body: string;
      prayer: string;
    };
    en: {
      title: string;
      body: string;
      prayer: string;
    };
  };
  themes: string[];
  specialUse: string[];
  quality: {
    status: string;
  };
  isFoundational?: boolean;
};

type DevotionalSeed = {
  entries: DevotionalEntry[];
};

const epoch = Date.UTC(1970, 0, 1);

function seedPath() {
  return path.join(process.cwd(), "..", "data", "devotional", "daily-verses.seed.json");
}

export function loadDevotionalSeed(): DevotionalEntry[] {
  const raw = fs.readFileSync(seedPath(), "utf-8");
  const data = JSON.parse(raw) as DevotionalSeed;
  return data.entries.filter((entry) => entry.quality.status === "polished");
}

export function getFoundationalVerse() {
  const entries = loadDevotionalSeed();
  const verse = entries.find((entry) => entry.isFoundational || entry.id === "dv-0001");
  if (!verse) {
    throw new Error("Foundational verse dv-0001 is missing.");
  }
  return verse;
}

export function selectDailyVerse(date = new Date(), specialUse?: string) {
  let entries = loadDevotionalSeed();
  if (specialUse) {
    const preferred = entries.filter((entry) => entry.specialUse.includes(specialUse));
    if (preferred.length > 0) {
      entries = preferred;
    }
  }
  const dayIndex = Math.floor((Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) - epoch) / 86_400_000);
  return entries[((dayIndex % entries.length) + entries.length) % entries.length];
}

