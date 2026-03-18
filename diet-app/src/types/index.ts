export interface MenuItem {
  id: string;
  label: string;
  time: string;
  calories: number;
  protein: number;
  calcium: number;
  isExercise?: boolean;
}

export interface DailyRecord {
  date: string;
  checklist: Record<string, boolean>;
  weight?: number;
}

export interface UserSettings {
  startDate: string;
  startWeight: number;
  targetWeight: number;
  darkMode: 'auto' | 'light' | 'dark';
}
