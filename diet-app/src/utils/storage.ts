import { DailyRecord, UserSettings } from '../types';

const RECORDS_KEY = 'diet-records';
const SETTINGS_KEY = 'diet-settings';

const defaultSettings: UserSettings = {
  startDate: new Date().toISOString().split('T')[0],
  startWeight: 67,
  targetWeight: 63,
  darkMode: 'auto',
};

export function getTodayKey(): string {
  return new Date().toISOString().split('T')[0];
}

export function getAllRecords(): Record<string, DailyRecord> {
  const raw = localStorage.getItem(RECORDS_KEY);
  return raw ? JSON.parse(raw) : {};
}

export function getDailyRecord(date: string): DailyRecord {
  const records = getAllRecords();
  return records[date] || { date, checklist: {} };
}

export function saveDailyRecord(record: DailyRecord): void {
  const records = getAllRecords();
  records[record.date] = record;
  localStorage.setItem(RECORDS_KEY, JSON.stringify(records));
}

export function getSettings(): UserSettings {
  const raw = localStorage.getItem(SETTINGS_KEY);
  return raw ? { ...defaultSettings, ...JSON.parse(raw) } : defaultSettings;
}

export function saveSettings(settings: UserSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export function getStreak(): number {
  const records = getAllRecords();
  let streak = 0;
  const today = new Date();

  for (let i = 0; i < 365; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const key = date.toISOString().split('T')[0];
    const record = records[key];

    if (record && Object.values(record.checklist).some(v => v)) {
      streak++;
    } else if (i > 0) {
      break;
    }
  }

  return streak;
}

export function getDaysSinceStart(): number {
  const settings = getSettings();
  const start = new Date(settings.startDate);
  const today = new Date();
  const diff = today.getTime() - start.getTime();
  return Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)) + 1);
}
