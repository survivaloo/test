import { useState } from 'react';
import { getSettings, saveSettings } from '../utils/storage';
import { UserSettings } from '../types';

export function SettingsView() {
  const [settings, setSettings] = useState<UserSettings>(getSettings);

  const update = (partial: Partial<UserSettings>) => {
    const updated = { ...settings, ...partial };
    setSettings(updated);
    saveSettings(updated);
  };

  return (
    <section className="px-4 pb-24">
      <h2 className="text-lg font-bold mb-4">設定</h2>

      <div className="space-y-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
          <h3 className="font-bold mb-3">目標設定</h3>
          <div className="space-y-3">
            <div>
              <label className="text-sm text-gray-500 dark:text-gray-400">開始日</label>
              <input
                type="date"
                value={settings.startDate}
                onChange={e => update({ startDate: e.target.value })}
                className="w-full mt-1 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-base"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm text-gray-500 dark:text-gray-400">開始体重 (kg)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.1"
                  value={settings.startWeight}
                  onChange={e => update({ startWeight: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-base"
                />
              </div>
              <div>
                <label className="text-sm text-gray-500 dark:text-gray-400">目標体重 (kg)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.1"
                  value={settings.targetWeight}
                  onChange={e => update({ targetWeight: parseFloat(e.target.value) || 0 })}
                  className="w-full mt-1 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-base"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
          <h3 className="font-bold mb-2">アプリ情報</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            1日1食ダイエット管理 v1.0.0
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            データはブラウザに保存されます
          </p>
        </div>
      </div>
    </section>
  );
}
