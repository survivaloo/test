interface Props {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: 'today', label: '今日', icon: '✅' },
  { id: 'graph', label: 'グラフ', icon: '📊' },
  { id: 'calendar', label: 'カレンダー', icon: '📅' },
  { id: 'settings', label: '設定', icon: '⚙️' },
];

export function Navigation({ currentTab, onTabChange }: Props) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 safe-area-bottom">
      <div className="max-w-lg mx-auto flex">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 flex flex-col items-center py-2 pt-3 transition-colors ${
              currentTab === tab.id
                ? 'text-accent dark:text-accent-light'
                : 'text-gray-400 dark:text-gray-500'
            }`}
          >
            <span className="text-xl mb-0.5">{tab.icon}</span>
            <span className="text-xs font-medium">{tab.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
