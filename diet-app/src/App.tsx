import { useState } from 'react';
import { Header } from './components/Header';
import { Checklist } from './components/Checklist';
import { NutritionMeter } from './components/NutritionMeter';
import { WeightInput } from './components/WeightInput';
import { Navigation } from './components/Navigation';
import { SettingsView } from './components/SettingsView';
import { ComingSoon } from './components/ComingSoon';
import { useChecklist } from './hooks/useChecklist';

function App() {
  const [tab, setTab] = useState('today');
  const { record, toggleItem, setWeight } = useChecklist();

  return (
    <div className="max-w-lg mx-auto min-h-screen pb-20">
      {tab === 'today' && (
        <>
          <Header />
          <Checklist record={record} onToggle={toggleItem} />
          <NutritionMeter record={record} />
          <WeightInput record={record} onSetWeight={setWeight} />
        </>
      )}
      {tab === 'graph' && <ComingSoon title="体重グラフ" icon="📊" />}
      {tab === 'calendar' && <ComingSoon title="カレンダー" icon="📅" />}
      {tab === 'settings' && <SettingsView />}
      <Navigation currentTab={tab} onTabChange={setTab} />
    </div>
  );
}

export default App;
