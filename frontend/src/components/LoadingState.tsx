export default function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 animate-fadeIn">
      <div className="relative">
        <div className="animate-spin rounded-full h-20 w-20 border-4 border-blue-200"></div>
        <div className="animate-spin rounded-full h-20 w-20 border-4 border-t-blue-600 border-r-purple-600 absolute top-0 left-0"></div>
      </div>
      <div className="mt-6 text-center space-y-2">
        <p className="text-xl font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Analyzing image with Claude AI...
        </p>
        <p className="text-sm text-gray-500">This may take a few seconds</p>
      </div>
      <div className="mt-6 flex gap-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
        <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
      </div>
    </div>
  );
}
