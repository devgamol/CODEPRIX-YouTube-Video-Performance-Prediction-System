export function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function getLetterGrade(score) {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

export function getPriorityOrder(priority) {
  switch (priority) {
    case 'High': return 1;
    case 'Medium': return 2;
    case 'Low': return 3;
    default: return 4;
  }
}