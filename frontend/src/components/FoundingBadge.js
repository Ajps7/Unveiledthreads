import { Gem } from 'lucide-react';

export const FoundingBadge = ({ size = 'md' }) => {
  const sm = size === 'sm';
  return (
    <span
      data-testid="founding-badge"
      className={`founding-badge inline-flex items-center gap-1.5 ${sm ? 'px-2 py-0.5 text-[9px]' : 'px-3 py-1 text-[10px]'} font-bold uppercase tracking-[0.2em] text-[#E8E8E8] select-none`}
      title="One of the first 40 independent brands on Unveiled Threads"
    >
      <Gem className={`${sm ? 'w-2.5 h-2.5' : 'w-3 h-3'} text-[#39FF14]`} />
      Founding Brand
    </span>
  );
};

export default FoundingBadge;
