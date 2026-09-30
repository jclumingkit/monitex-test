export { cn } from "cn";

export const humanize = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());

const formatDateValue = (
  value: string,
  options: Intl.DateTimeFormatOptions,
) => {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    ...options,
  }).format(date);
};

export const formatDate = (value: string) =>
  formatDateValue(value, { dateStyle: "medium", timeStyle: "medium" });

export const formatDateOnly = (value: string) =>
  formatDateValue(value, { dateStyle: "medium" });

export const formatTime = (value: string) =>
  formatDateValue(value, { timeStyle: "medium" });
