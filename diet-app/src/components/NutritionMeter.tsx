import { menuItems, nutritionTargets } from '../data/menuItems';
import { DailyRecord } from '../types';

interface Props {
  record: DailyRecord;
}

export function NutritionMeter({ record }: Props) {
  const totals = menuItems.reduce(
    (acc, item) => {
      if (record.checklist[item.id]) {
        acc.calories += item.calories;
        acc.protein += item.protein;
        acc.calcium += item.calcium;
      }
      return acc;
    },
    { calories: 0, protein: 0, calcium: 0 }
  );

  const metrics = [
    {
      key: 'calories' as const,
      current: totals.calories,
      ...nutritionTargets.calories,
      color: 'bg-emerald-500',
      bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
    },
    {
      key: 'protein' as const,
      current: totals.protein,
      ...nutritionTargets.protein,
      color: 'bg-blue-500',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    },
    {
      key: 'calcium' as const,
      current: totals.calcium,
      ...nutritionTargets.calcium,
      color: 'bg-purple-500',
      bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    },
  ];

  return (
    <section className="px-4 mb-4">
      <h2 className="text-base font-bold mb-3">栄養バランス</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm space-y-3">
        {metrics.map(m => {
          const percentage = Math.min(100, Math.max(0, (Math.abs(m.current) / m.target) * 100));
          return (
            <div key={m.key}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium">{m.label}</span>
                <span className="text-gray-500 dark:text-gray-400">
                  {m.key === 'calories' && m.current < 0 ? '' : ''}
                  {Math.abs(Math.round(m.current))}{m.unit}
                  <span className="text-gray-400 dark:text-gray-500"> / {m.target}{m.unit}</span>
                </span>
              </div>
              <div className={`h-3 rounded-full ${m.bgColor}`}>
                <div
                  className={`progress-bar ${m.color}`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
