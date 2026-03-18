import { getDaysSinceStart, getStreak } from '../utils/storage';
import { useTheme } from '../hooks/useTheme';

const themeIcons: Record<string, string> = {
  auto: '🌗',
  light: '☀️',
  dark: '🌙',
};

export function Header() {
  const { mode, cycleTheme } = useTheme();
  const days = getDaysSinceStart();
  const streak = getStreak();

  const today = new Date();
  const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
  const dateStr = `${today.getFullYear()}年${today.getMonth() + 1}月${today.getDate()}日（${weekdays[today.getDay()]}）`;

  return (
    <header className="text-center py-4 px-4">
      <div className="flex justify-between items-center mb-2">
        <h1 className="text-lg font-bold text-accent dark:text-accent-light">
          1日1食ダイエット
        </h1>
        <button
          onClick={cycleTheme}
          className="text-xl p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          aria-label="テーマ切替"
        >
          {themeIcons[mode]}
        </button>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{dateStr}</p>
      <div className="flex justify-center gap-4 mt-2">
        <span className="inline-flex items-center gap-1 text-sm font-medium bg-accent/10 text-accent dark:text-accent-light px-3 py-1 rounded-full">
          {days}日目
        </span>
        {streak > 1 && (
          <span className="inline-flex items-center gap-1 text-sm font-medium bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400 px-3 py-1 rounded-full">
            🔥 {streak}日連続
          </span>
        )}
      </div>
    </header>
  );
}
