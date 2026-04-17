"use client";

const STEPS = [
  { num: 1, label: "ファイルアップロード" },
  { num: 2, label: "会議情報入力" },
  { num: 3, label: "お支払い" },
  { num: 4, label: "生成・ダウンロード" },
];

export function StepBar({ current }: { current: 1 | 2 | 3 | 4 }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {STEPS.map((step, i) => (
        <div key={step.num} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${
                step.num < current
                  ? "bg-green-500 border-green-500 text-white"
                  : step.num === current
                  ? "bg-red-500 border-red-500 text-white"
                  : "bg-white border-gray-300 text-gray-400"
              }`}
            >
              {step.num < current ? "✓" : step.num}
            </div>
            <span
              className={`mt-1 text-xs whitespace-nowrap ${
                step.num === current ? "text-red-600 font-semibold" : "text-gray-400"
              }`}
            >
              {step.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div
              className={`w-12 h-0.5 mb-5 mx-1 ${
                step.num < current ? "bg-green-400" : "bg-gray-200"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}
