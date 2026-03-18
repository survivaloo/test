import { MenuItem } from '../types';

export const menuItems: MenuItem[] = [
  {
    id: 'tea',
    label: '紅茶',
    time: '朝',
    calories: 2,
    protein: 0,
    calcium: 0,
  },
  {
    id: 'milk-umeboshi',
    label: '牛乳 + 梅干し',
    time: '朝風呂後',
    calories: 137,
    protein: 6.6,
    calcium: 224,
  },
  {
    id: 'miso-soup',
    label: 'インスタント味噌汁',
    time: '昼',
    calories: 30,
    protein: 2.0,
    calcium: 30,
  },
  {
    id: 'coffee',
    label: 'コーヒー',
    time: '日中',
    calories: 0,
    protein: 0,
    calcium: 0,
  },
  {
    id: 'dinner',
    label: '夕食（煮卵・キャベツ・カレー・牛乳）',
    time: '夕食',
    calories: 600,
    protein: 31.2,
    calcium: 409,
  },
  {
    id: 'vitamin-d',
    label: 'ビタミンDサプリ',
    time: '夕食時',
    calories: 0,
    protein: 0,
    calcium: 0,
  },
  {
    id: 'walking',
    label: '徒歩通勤（往復60分）',
    time: '毎日',
    calories: -250,
    protein: 0,
    calcium: 0,
    isExercise: true,
  },
];

export const nutritionTargets = {
  calories: { target: 1060, label: 'カロリー', unit: 'kcal' },
  protein: { target: 45, label: 'タンパク質', unit: 'g' },
  calcium: { target: 1100, label: 'カルシウム', unit: 'mg' },
} as const;
