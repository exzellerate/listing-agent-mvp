import { Platform } from '../types';

interface PlatformSelectorProps {
  selected: Platform;
  onChange: (platform: Platform) => void;
  disabled?: boolean;
}

const platforms: { value: Platform; label: string; gradient: string; hoverGradient: string; icon: string }[] = [
  {
    value: 'ebay',
    label: 'eBay',
    gradient: 'from-yellow-400 to-yellow-600',
    hoverGradient: 'from-yellow-500 to-yellow-700',
    icon: '🏷️'
  },
  {
    value: 'amazon',
    label: 'Amazon',
    gradient: 'from-orange-400 to-orange-600',
    hoverGradient: 'from-orange-500 to-orange-700',
    icon: '📦'
  },
  {
    value: 'walmart',
    label: 'Walmart',
    gradient: 'from-blue-400 to-blue-600',
    hoverGradient: 'from-blue-500 to-blue-700',
    icon: '🛒'
  },
];

export default function PlatformSelector({
  selected,
  onChange,
  disabled = false,
}: PlatformSelectorProps) {
  return (
    <div className="space-y-3">
      <label className="block text-lg font-semibold text-gray-800">
        Select Target Platform
      </label>
      <div className="grid grid-cols-3 gap-4">
        {platforms.map((platform) => (
          <button
            key={platform.value}
            onClick={() => onChange(platform.value)}
            disabled={disabled}
            className={`
              relative px-6 py-5 rounded-xl font-bold text-white text-lg transition-all duration-300 transform
              ${selected === platform.value
                ? `bg-gradient-to-br ${platform.gradient} scale-105 shadow-2xl ring-4 ring-white ring-offset-2`
                : `bg-gradient-to-br ${platform.gradient} opacity-60 hover:opacity-100 hover:scale-102 shadow-lg`
              }
              ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:shadow-xl'}
            `}
            aria-pressed={selected === platform.value}
          >
            <div className="flex flex-col items-center gap-2">
              <span className="text-3xl">{platform.icon}</span>
              <span>{platform.label}</span>
              {selected === platform.value && (
                <div className="absolute -top-2 -right-2 bg-white rounded-full p-1 shadow-lg">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
