import { Platform } from '../types';

interface PlatformSelectorProps {
  selected: Platform;
  onChange: (platform: Platform) => void;
  disabled?: boolean;
}

const platforms: { value: Platform; label: string; color: string }[] = [
  { value: 'ebay', label: 'eBay', color: 'bg-yellow-500 hover:bg-yellow-600' },
  { value: 'amazon', label: 'Amazon', color: 'bg-orange-500 hover:bg-orange-600' },
  { value: 'walmart', label: 'Walmart', color: 'bg-blue-500 hover:bg-blue-600' },
];

export default function PlatformSelector({
  selected,
  onChange,
  disabled = false,
}: PlatformSelectorProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Target Platform
      </label>
      <div className="flex gap-3">
        {platforms.map((platform) => (
          <button
            key={platform.value}
            onClick={() => onChange(platform.value)}
            disabled={disabled}
            className={`
              flex-1 px-4 py-3 rounded-lg font-semibold text-white transition-all
              ${selected === platform.value ? platform.color + ' ring-4 ring-offset-2 ring-opacity-50' : 'bg-gray-300 hover:bg-gray-400'}
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            aria-pressed={selected === platform.value}
          >
            {platform.label}
          </button>
        ))}
      </div>
    </div>
  );
}
