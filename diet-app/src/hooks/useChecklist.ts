import { useState, useEffect, useCallback } from 'react';
import { DailyRecord } from '../types';
import { getTodayKey, getDailyRecord, saveDailyRecord } from '../utils/storage';

export function useChecklist() {
  const todayKey = getTodayKey();
  const [record, setRecord] = useState<DailyRecord>(() => getDailyRecord(todayKey));

  useEffect(() => {
    const key = getTodayKey();
    if (key !== record.date) {
      setRecord(getDailyRecord(key));
    }
  }, [record.date]);

  const toggleItem = useCallback((itemId: string) => {
    setRecord(prev => {
      const updated = {
        ...prev,
        checklist: {
          ...prev.checklist,
          [itemId]: !prev.checklist[itemId],
        },
      };
      saveDailyRecord(updated);
      return updated;
    });
  }, []);

  const setWeight = useCallback((weight: number | undefined) => {
    setRecord(prev => {
      const updated = { ...prev, weight };
      saveDailyRecord(updated);
      return updated;
    });
  }, []);

  return { record, toggleItem, setWeight };
}
