const ALL_SIZES = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'One Size'];

/**
 * Size chip toggler for the AddProduct form.
 */
export function ProductSizes({ sizes, onToggle }) {
  return (
    <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
      <h2 className="text-lg font-bold text-white uppercase mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
        Available Sizes *
      </h2>
      <p className="text-xs text-[#9CA3AF] mb-4">Select all sizes you have in stock</p>

      <div className="flex flex-wrap gap-2" data-testid="size-selector">
        {ALL_SIZES.map((size) => (
          <button
            key={size}
            type="button"
            onClick={() => onToggle(size)}
            className={`px-5 py-2.5 border text-sm font-medium transition-all ${
              sizes.includes(size)
                ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]'
                : 'border-white/20 text-[#9CA3AF] hover:border-white/40 hover:text-white'
            }`}
            data-testid={`size-toggle-${size}`}
          >
            {size}
          </button>
        ))}
      </div>
      {sizes.length > 0 && (
        <p className="text-xs text-[#39FF14] mt-3">Selected: {sizes.join(', ')}</p>
      )}
    </div>
  );
}
