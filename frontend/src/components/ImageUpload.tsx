import { useRef, useState, useEffect, DragEvent } from 'react';
import { Upload, Image } from 'lucide-react';
import { MAX_IMAGES } from '../constants';

interface ImageFile {
  file: File;
  preview: string;
}

interface ImageUploadProps {
  onImagesSelect: (files: File[]) => void;
  onContextChange?: (context: string) => void;
  disabled?: boolean;
  selectedFiles?: File[];
  userContext?: string;
  hideUploadArea?: boolean;
}

const isHeic = (file: File): boolean => {
  const name = file.name.toLowerCase();
  return name.endsWith('.heic') || name.endsWith('.heif') ||
    file.type === 'image/heic' || file.type === 'image/heif';
};

export default function ImageUpload({ onImagesSelect, onContextChange, disabled = false, selectedFiles = [], userContext = '', hideUploadArea = false }: ImageUploadProps) {
  const [images, setImages] = useState<ImageFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [context, setContext] = useState(userContext);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [brokenPreviews, setBrokenPreviews] = useState<Set<number>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);

  // DEBUG: Log whether onContextChange prop is provided on mount
  useEffect(() => {
    console.log('ImageUpload mounted. onContextChange prop:', typeof onContextChange, onContextChange ? 'PROVIDED' : 'NOT PROVIDED');
  }, []);

  // Resync internal `images` state with the parent's `selectedFiles`. Today
  // the only caller-driven change is clearing to empty (e.g. "Start Over"),
  // detected via a content signature rather than just `.length` so a
  // same-length-but-different-set reset wouldn't silently no-op.
  useEffect(() => {
    const parentSignature = selectedFiles.map(f => `${f.name}:${f.size}`).join(',');
    const localSignature = images.map(img => `${img.file.name}:${img.file.size}`).join(',');
    if (selectedFiles.length === 0 && parentSignature !== localSignature) {
      setImages([]);
      setBrokenPreviews(new Set());
    }
  }, [selectedFiles, images]);

  const validateAndAddFiles = (newFiles: FileList | File[]) => {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'];
    const maxSize = 10 * 1024 * 1024; // 10MB
    const maxImages = MAX_IMAGES;

    const filesArray = Array.from(newFiles);
    const currentCount = images.length;

    // Check if adding these files would exceed the limit
    if (currentCount + filesArray.length > maxImages) {
      setValidationError(`Maximum ${maxImages} images allowed. You currently have ${currentCount}.`);
      return;
    }

    const validFiles: ImageFile[] = [];
    // Tracks name+size of every file already added or accepted earlier in
    // this same batch, so duplicates (re-added file, or the same file picked
    // twice in one dialog) are caught before they're queued for preview.
    const seenKeys = new Set(images.map(img => `${img.file.name}:${img.file.size}`));
    let hadError = false;
    let expectedCount = 0;

    for (const file of filesArray) {
      const key = `${file.name}:${file.size}`;

      if (isHeic(file)) {
        setValidationError(`"${file.name}" is a HEIC/HEIF photo, which isn't supported. Export it as JPEG or PNG (on iPhone: Settings > Camera > Formats > Most Compatible) and try again.`);
        hadError = true;
        continue;
      }

      if (seenKeys.has(key)) {
        setValidationError(`"${file.name}" has already been added.`);
        hadError = true;
        continue;
      }

      // Validate file type
      if (!allowedTypes.includes(file.type)) {
        setValidationError(`"${file.name}" is not a supported format. Use JPG, PNG, WebP, or GIF.`);
        hadError = true;
        continue;
      }

      // Validate file size
      if (file.size > maxSize) {
        setValidationError(`"${file.name}" (${(file.size / 1024 / 1024).toFixed(1)}MB) exceeds the 10MB limit.`);
        hadError = true;
        continue;
      }

      seenKeys.add(key);
      expectedCount++;

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        validFiles.push({
          file,
          preview: reader.result as string,
        });

        // When all accepted files are processed, update state
        if (validFiles.length === expectedCount) {
          const updatedImages = [...images, ...validFiles];
          setImages(updatedImages);
          onImagesSelect(updatedImages.map(img => img.file));
          if (!hadError) setValidationError(null);
        }
      };
      reader.onerror = () => {
        setValidationError(`Failed to read "${file.name}". Please try again.`);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
    }
  };

  const handleClick = () => {
    if (!disabled && images.length < MAX_IMAGES) {
      fileInputRef.current?.click();
    }
  };

  const removeImage = (index: number) => {
    const updatedImages = images.filter((_, i) => i !== index);
    setImages(updatedImages);
    onImagesSelect(updatedImages.map(img => img.file));
    setBrokenPreviews(prev => {
      const next = new Set<number>();
      prev.forEach(i => {
        if (i < index) next.add(i);
        else if (i > index) next.add(i - 1);
      });
      return next;
    });
  };

  const handleContextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newContext = e.target.value;
    console.log('ImageUpload: handleContextChange called with:', JSON.stringify(newContext));
    setContext(newContext);
    console.log('ImageUpload: local context state updated to:', JSON.stringify(newContext));
    if (onContextChange) {
      console.log('ImageUpload: calling onContextChange callback with:', JSON.stringify(newContext));
      onContextChange(newContext);
    } else {
      console.warn('ImageUpload: onContextChange callback is not provided!');
    }
  };

  return (
    <div className="w-full">
      {/* Thumbnails with Preview Badge */}
      {images.length > 0 && (
        <div className="mb-6">
          <div className="inline-block bg-gray-100 text-gray-700 text-xs font-medium px-3 py-1.5 rounded-md mb-3">
            Preview
          </div>
          <div className="flex flex-wrap gap-2">
            {images.map((img, idx) => (
              <div key={idx} className="relative group">
                <div className="relative w-20 h-20 flex-shrink-0 bg-gray-50 rounded-lg border-2 border-gray-200 overflow-hidden">
                  <img
                    src={img.preview}
                    alt={`Product ${idx + 1}`}
                    className="w-full h-full object-contain"
                    onError={() => setBrokenPreviews(prev => new Set(prev).add(idx))}
                  />
                  {brokenPreviews.has(idx) && (
                    <div className="absolute inset-0 flex items-center justify-center bg-red-50 text-red-600 text-[10px] text-center px-1 leading-tight">
                      Couldn't preview — file may be corrupted
                    </div>
                  )}
                </div>
                {idx === 0 && (
                  <div className="absolute top-1 left-1 bg-black text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
                    Primary
                  </div>
                )}
                <button
                  onClick={() => removeImage(idx)}
                  disabled={disabled}
                  className="absolute top-1 right-1 bg-white text-gray-700 rounded-full w-5 h-5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg hover:bg-gray-100 disabled:opacity-50 font-bold text-sm leading-none"
                  aria-label={`Remove image ${idx + 1}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Area - Matching Mockup Design */}
      {images.length < MAX_IMAGES && !hideUploadArea && (
        <div className="bg-white rounded-2xl border-2 border-gray-200 p-8">
          <div
            onClick={handleClick}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-xl py-16 px-8 text-center cursor-pointer
              transition-all duration-200
              ${dragActive ? 'border-gray-400 bg-gray-50' : 'border-gray-300 hover:border-gray-400'}
              ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept="image/*"
              multiple
              onChange={handleChange}
              disabled={disabled}
              aria-label="Upload product images"
            />

            <div className="flex flex-col items-center space-y-6">
              {/* Upload Icon */}
              <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
                <Upload className="w-8 h-8 text-gray-500" />
              </div>

              {/* Text and Button */}
              <div className="space-y-4">
                <p className="text-base text-gray-600">
                  Drag and drop your product image here, or
                </p>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleClick();
                  }}
                  disabled={disabled}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Image className="w-4 h-4" />
                  Browse Files
                </button>

                <p className="text-sm text-gray-500">
                  Supports: JPG, PNG, WEBP (Max 10MB)
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Inline Validation Error */}
      {validationError && (
        <div className="mt-3 flex items-center gap-2 text-red-600 text-sm">
          <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span>{validationError}</span>
          <button onClick={() => setValidationError(null)} className="ml-auto text-red-400 hover:text-red-600">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}

      {images.length > 1 && (
        <div className="mt-4 text-sm text-gray-600 bg-blue-50 p-4 rounded-lg border border-blue-100">
          <span className="font-semibold">Multiple images detected:</span> All images will be analyzed and cross-referenced for better accuracy.
        </div>
      )}

      {/* User Context Input */}
      {images.length > 0 && (
        <div className="mt-4">
          <label htmlFor="user-context" className="block text-sm font-medium text-gray-700 mb-2">
            Additional Details (Optional)
          </label>
          <input
            id="user-context"
            type="text"
            value={context}
            onChange={handleContextChange}
            disabled={disabled}
            placeholder="e.g., Aja Wilson size 10, iPhone 12 Pro Max, Nike Air Jordan 1..."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-black focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="mt-2 text-xs text-gray-500">
            Help us identify your product more accurately by providing specific details like brand, model, size, or unique features.
          </p>
        </div>
      )}
    </div>
  );
}
