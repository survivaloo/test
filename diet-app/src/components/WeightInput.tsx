import { useState } from 'react';
import { DailyRecord } from '../types';
import { getSettings } from '../utils/storage';

interface Props {
  record: DailyRecord;
  onSetWeight: (weight: number | undefined) => void;
}

export function WeightInput({ record, onSetWeight }: Props) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(record.weight?.toString() ?? '');
  const settings = getSettings();
  const diff = record.weight != null ? record.weight - settings.targetWeight : null;

  const handleSave = () => {
    const num = parseFloat(value);
    if (!isNaN(num) && num > 0 && num < 300) {
      onSetWeight(num);
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <section className="px-4 mb-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
          <h2 className="text-base font-bold mb-3">体重記録</h2>
          <div className="flex items-center gap-2">
            <input
              type="number"
              inputMode="decimal"
              step="0.1"
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              className="flex-1 text-2xl font-bold text-center bg-gray-50 dark:bg-gray-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-accent"
              autoFocus
              placeholder="67.0"
            />
            <span className="text-lg text-gray-500">kg</span>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleSave}
              className="flex-1 bg-accent text-white font-bold py-2 rounded-lg active:scale-95 transition-transform"
            >
              保存
            </button>
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 text-gray-500 dark:text-gray-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              キャンセル
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="px-4 mb-4">
      <button
        onClick={() => {
          setValue(record.weight?.toString() ?? '');
          setEditing(true);
        }}
        className="w-full bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm text-left active:scale-[0.98] transition-transform"
      >
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-base font-bold mb-1">体重記録</h2>
            {record.weight != null ? (
              <div>
                <span className="text-2xl font-bold">{record.weight}</span>
                <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">kg</span>
                {diff != null && (
                  <span className={`text-sm ml-2 ${diff <= 0 ? 'text-accent' : 'text-orange-500'}`}>
                    目標まで {diff > 0 ? '+' : ''}{diff.toFixed(1)}kg
                  </span>
                )}
              </div>
            ) : (
              <span className="text-gray-400 dark:text-gray-500">タップして記録</span>
            )}
          </div>
          <span className="text-2xl">📝</span>
        </div>
      </button>
    </section>
  );
}
