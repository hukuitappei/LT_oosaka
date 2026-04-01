export const CATEGORY_LABELS: Record<string, string> = {
  security: "Security",
  performance: "Performance",
  design: "Design",
  testing: "Testing",
  code_quality: "Code Quality",
  other: "Other",
}

export const CATEGORY_COLORS: Record<string, string> = {
  security: "bg-red-100 text-red-800",
  performance: "bg-yellow-100 text-yellow-800",
  design: "bg-fuchsia-100 text-fuchsia-800",
  testing: "bg-green-100 text-green-800",
  code_quality: "bg-blue-100 text-blue-800",
  other: "bg-gray-100 text-gray-800",
}

export const LEARNING_STATUS_LABELS: Record<string, string> = {
  new: "New",
  in_progress: "In Progress",
  applied: "Applied",
  ignored: "Ignored",
}

export const LEARNING_STATUS_COLORS: Record<string, string> = {
  new: "border-amber-300/30 bg-amber-300/15 text-amber-100",
  in_progress: "border-sky-300/30 bg-sky-300/15 text-sky-100",
  applied: "border-emerald-300/30 bg-emerald-300/15 text-emerald-100",
  ignored: "border-stone-300/20 bg-stone-300/10 text-stone-300",
}
