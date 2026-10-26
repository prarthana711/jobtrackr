const TONES = {
  good: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  bad: "bg-red-50 text-red-700 ring-red-200",
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
};

export default function SkillChips({ skills, tone = "neutral", empty = "None" }) {
  if (!skills || skills.length === 0) {
    return <p className="text-sm text-slate-500">{empty}</p>;
  }
  return (
    <ul className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <li
          key={skill}
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}
        >
          {skill}
        </li>
      ))}
    </ul>
  );
}