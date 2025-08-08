
interface ProcessingStage {
  id: string;
  name: string;
  message: string;
  progress: number;
  status: 'pending' | 'active' | 'completed' | 'error';
  agent: string;
}

interface ProcessingStagesProps {
  currentStage?: ProcessingStage;
  allStages: ProcessingStage[];
  className?: string;
}

// Agent icons mapping
const getAgentIcon = (agent: string) => {
  switch (agent) {
    case 'legal':
      return '⚖️';
    case 'technical':
      return '🔧';
    case 'ai_enhanced':
      return '🤖';
    case 'system':
      return '⚙️';
    default:
      return '🔄';
  }
};

// Agent colors mapping
const getAgentColor = (agent: string) => {
  switch (agent) {
    case 'legal':
      return 'text-blue-600 bg-blue-100';
    case 'technical':
      return 'text-green-600 bg-green-100';
    case 'ai_enhanced':
      return 'text-purple-600 bg-purple-100';
    case 'system':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-indigo-600 bg-indigo-100';
  }
};

export default function ProcessingStages({ 
  currentStage, 
  allStages, 
  className = '' 
}: ProcessingStagesProps) {
  if (!currentStage) {
    return null;
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      {/* Current Stage Display */}
      <div className="flex items-center space-x-3 mb-4">
        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${getAgentColor(currentStage.agent)}`}>
          <span className="text-lg">{getAgentIcon(currentStage.agent)}</span>
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900">{currentStage.name}</h3>
            <span className="text-sm text-gray-500">{Math.round(currentStage.progress)}%</span>
          </div>
          <p className="text-sm text-gray-600 mt-1">{currentStage.message}</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${currentStage.progress}%` }}
          ></div>
        </div>
      </div>

      {/* Stage List */}
      <div className="space-y-2">
        {allStages.map((stage) => {
          let statusIcon;
          let statusColor;
          
          if (stage.status === 'completed') {
            statusIcon = '✅';
            statusColor = 'text-green-600';
          } else if (stage.status === 'active') {
            statusIcon = '🔄';
            statusColor = 'text-blue-600';
          } else if (stage.status === 'error') {
            statusIcon = '❌';
            statusColor = 'text-red-600';
          } else {
            statusIcon = '⏳';
            statusColor = 'text-gray-400';
          }

          return (
            <div 
              key={stage.id}
              className={`flex items-center space-x-3 p-2 rounded transition-all duration-300 ${
                stage.status === 'active' ? 'bg-blue-50 border border-blue-200' : 
                stage.status === 'completed' ? 'bg-green-50' : 'bg-gray-50'
              }`}
            >
              <span className="text-sm">{statusIcon}</span>
              <span className={`text-sm font-medium ${statusColor}`}>
                {stage.name}
              </span>
              {stage.status === 'active' && (
                <div className="ml-auto">
                  <div className="flex space-x-1">
                    <div className="w-1 h-1 bg-blue-600 rounded-full animate-bounce"></div>
                    <div className="w-1 h-1 bg-blue-600 rounded-full animate-bounce delay-100"></div>
                    <div className="w-1 h-1 bg-blue-600 rounded-full animate-bounce delay-200"></div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Agents Working Indicator - Enhanced */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-3 border border-blue-200">
          <div className="flex items-center justify-center space-x-4">
            <div className="flex space-x-1">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-bounce delay-100"></div>
              <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce delay-200"></div>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-sm font-semibold text-blue-700">🤖 AI Agents Working</span>
              <span className="text-xs text-blue-600 mt-0.5">Processing your request...</span>
            </div>
            <div className="flex space-x-1">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce delay-300"></div>
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-bounce delay-400"></div>
              <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce delay-500"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}