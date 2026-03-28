export const COLOR_RANGES = {
  green: { min: 1, max: 5 },
  yellow: { min: 6, max: 10 },
  red: { min: 11, max: Infinity },
};

export const getWorkloadColor = (value: number): string => {
  if (value >= COLOR_RANGES.green.min && value <= COLOR_RANGES.green.max) {
    return "#588756"; // green
  }

  if (value >= COLOR_RANGES.yellow.min && value <= COLOR_RANGES.yellow.max) {
    return "#B06A35"; // yellow
  }

  if (value >= COLOR_RANGES.red.min) {
    return "#821B1B"; // red
  }

  return "#595d63";
};
