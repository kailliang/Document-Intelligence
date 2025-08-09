
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
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-3 ${className}`}>
      {/* Current Stage Display - Compact */}
      <div className="flex items-center space-x-3 mb-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getAgentColor(currentStage.agent)}`}>
          <span className="text-sm">{getAgentIcon(currentStage.agent)}</span>
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900">{currentStage.name}</h3>
            <span className="text-xs text-gray-500">{Math.round(currentStage.progress)}%</span>
          </div>
        </div>
      </div>

      {/* Progress Bar - Thinner */}
      <div className="mb-3">
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div 
            className="bg-blue-600 h-1.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${currentStage.progress}%` }}
          ></div>
        </div>
      </div>

      {/* Stage List - Compact */}
      <div className="space-y-1">
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
              className={`flex items-center space-x-2 py-1.5 px-2 rounded transition-all duration-300 ${
                stage.status === 'active' ? 'bg-blue-50 border border-blue-200' : 
                stage.status === 'completed' ? 'bg-green-50' : ''
              }`}
            >
              <span className="text-xs">{statusIcon}</span>
              <span className={`text-xs font-medium ${statusColor} flex-1`}>
                {stage.name}
              </span>
              {stage.status === 'active' && (
                <div className="flex space-x-0.5">
                  <div className="w-1 h-1 bg-blue-600 rounded-full animate-bounce"></div>
                  <div className="w-1 h-1 bg-blue-600 rounded-full animate-bounce delay-100"></div>
                  <div className="w-1 h-1 bg-blue-600 rounded-full animate-bounce delay-200"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Agents Working Indicator - Compact */}
      <div className="mt-3 pt-2 border-t border-gray-100">
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-md p-2 border border-blue-200">
          <div className="flex items-center justify-center space-x-3">
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-1 h-1 bg-green-500 rounded-full animate-bounce delay-100"></div>
              <div className="w-1 h-1 bg-purple-500 rounded-full animate-bounce delay-200"></div>
            </div>
            <span className="text-xs font-semibold text-blue-700">🤖 AI Agents Working</span>
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce delay-300"></div>
              <div className="w-1 h-1 bg-green-500 rounded-full animate-bounce delay-400"></div>
              <div className="w-1 h-1 bg-purple-500 rounded-full animate-bounce delay-500"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}