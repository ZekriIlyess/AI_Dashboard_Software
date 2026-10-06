import React from "react";
import styles from "../../app/(dashboard)/explore/explore.module.css";

interface QuestionQueueProps {
  queue: string[];
  setQueue: (val: string[]) => void;
  editingQueueIndex: number | null;
  setEditingQueueIndex: (val: number | null) => void;
  editingQueueText: string;
  setEditingQueueText: (val: string) => void;
}

export default function QuestionQueue({
  queue,
  setQueue,
  editingQueueIndex,
  setEditingQueueIndex,
  editingQueueText,
  setEditingQueueText
}: QuestionQueueProps) {
  if (queue.length === 0) return null;

  return (
    <div className={styles.queuePanel}>
      <h3 className={styles.queueHeader}>
        QUEUED QUESTIONS ({queue.length})
      </h3>
      <div className={styles.queueList}>
        {queue.map((q, idx) => (
          <div key={idx} className={styles.queueItem}>
            {editingQueueIndex === idx ? (
              <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
                <input
                  type="text"
                  value={editingQueueText}
                  onChange={(e) => setEditingQueueText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      const newQ = [...queue];
                      newQ[idx] = editingQueueText;
                      setQueue(newQ);
                      setEditingQueueIndex(null);
                    } else if (e.key === "Escape") {
                      setEditingQueueIndex(null);
                    }
                  }}
                  autoFocus
                  className={styles.queueInput}
                />
                <button 
                  onClick={() => {
                    const newQ = [...queue];
                    newQ[idx] = editingQueueText;
                    setQueue(newQ);
                    setEditingQueueIndex(null);
                  }}
                  className={styles.queueBtn}
                >
                  Save
                </button>
              </div>
            ) : (
              <>
                <span className={styles.queueText}>{q}</span>
                <div className={styles.queueActions}>
                  <button 
                    onClick={() => {
                      setEditingQueueIndex(idx);
                      setEditingQueueText(q);
                    }}
                    className={styles.queueBtn}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => {
                      setQueue(queue.filter((_, i) => i !== idx));
                    }}
                    className={styles.queueBtn}
                  >
                    Remove
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
