import { useCallback, useEffect, useState } from 'react';
import { listClassStatuses, setClassStatus } from '../api/classes';
import type { ClassStatus, ClassStatusMap } from '../api/classes';

/** Profile class statuses (FC21) + a saver. Loader/saver are DI seams so
    stories can inject fixtures; a failed load just leaves the map empty. */
export function useClassStatuses(
  load: () => Promise<ClassStatusMap> = listClassStatuses,
  save: (courseId: string, status: ClassStatus) => Promise<ClassStatus> = setClassStatus,
) {
  const [statuses, setStatuses] = useState<ClassStatusMap>({});
  useEffect(() => {
    let cancelled = false;
    load().then((map) => !cancelled && setStatuses(map)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [load]);
  const changeStatus = useCallback(
    async (courseId: string, next: ClassStatus) => {
      const saved = await save(courseId, next);
      setStatuses((prev) => ({ ...prev, [courseId]: saved }));
    },
    [save],
  );
  return { statuses, changeStatus };
}
