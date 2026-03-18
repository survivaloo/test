import { menuItems } from '../data/menuItems';
import { DailyRecord } from '../types';

interface Props {
  record: DailyRecord;
  onToggle: (itemId: string) => void;
}

export function Checklist({ record, onToggle }: Props) {
  const completedCount = menuItems.filter(item => record.checklist[item.id]).length;
  const totalCount = menuItems.length;

  return (
    <section className="px-4 mb-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-base font-bold">今日のチェックリスト</h2>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {completedCount}/{totalCount}
        </span>
      </div>
      <div className="space-y-2">
        {menuItems.map(item => {
          const checked = !!record.checklist[item.id];
          return (
            <button
              key={item.id}
              onClick={() => onToggle(item.id)}
              className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-200 active:scale-[0.98] ${
                checked
                  ? 'bg-accent/10 dark:bg-accent/20'
                  : 'bg-white dark:bg-gray-800 shadow-sm'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
                  checked
                    ? 'bg-accent border-accent text-white'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
              >
                {checked && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <div className="flex-1 text-left">
                <span className={`text-base ${checked ? 'line-through text-gray-400 dark:text-gray-500' : ''}`}>
                  {item.label}
                </span>
              </div>
              <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
                {item.time}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
