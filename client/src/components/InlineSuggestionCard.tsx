import React from 'react';

interface Suggestion {
  id: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  original_text: string;
  replace_to: string;
  confidence: number;
  agent: 'technical' | 'legal' | 'novelty' | 'lead';
  created_at: string;
}

interface InlineSuggestionCardProps {
  suggestions: Suggestion[];
  onAccept: (cardId: string) => void;
  onDismiss: (cardId: string) => void;
  onCopy: (cardId: string) => void;
  className?: string;
}

const InlineSuggestionCard: React.FC<InlineSuggestionCardProps> = ({
  suggestions,
  onAccept,
  onDismiss,
  onCopy,
  className = ''
}) => {
  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'border-red-500 bg-red-50';
      case 'medium':
        return 'border-yellow-500 bg-yellow-50';
      case 'low':
        return 'border-blue-500 bg-blue-50';
      default:
        return 'border-gray-500 bg-gray-50';
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'Critical';
      case 'medium':
        return 'Medium';
      case 'low':
        return 'Minor';
      default:
        return severity;
    }
  };

  const getSeverityBadgeColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-200 text-red-800';
      case 'medium':
        return 'bg-yellow-200 text-yellow-800';
      case 'low':
        return 'bg-blue-200 text-blue-800';
      default:
        return 'bg-gray-200 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const getConfidenceBarColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-medium text-gray-700">AI Analysis Results</span>
        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
          {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''}
        </span>
      </div>
      
      {suggestions.map((suggestion) => (
        <div
          key={suggestion.id}
          className={`p-3 rounded-lg border-l-4 ${getSeverityColor(suggestion.severity)} transition-all duration-200 w-full`}
        >
          {/* Suggestion header */}
          <div className="flex items-center gap-1 mb-3 flex-wrap">
            <span className="text-xs font-medium text-gray-600 shrink-0">
              P{suggestion.paragraph}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${getSeverityBadgeColor(suggestion.severity)} shrink-0`}>
              {getSeverityLabel(suggestion.severity)}
            </span>
            <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded text-center min-w-0 truncate">
              {suggestion.type}
            </span>
          </div>

          {/* Problem description */}
          <p className="text-sm text-gray-700 mb-3 leading-relaxed">
            {suggestion.description}
          </p>

          {/* Original text preview */}
          {suggestion.original_text && (
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-600 mb-1">Original text:</p>
              <div className="bg-gray-100 p-2 rounded text-sm text-gray-700 font-mono">
                {suggestion.original_text.length > 100 
                  ? suggestion.original_text.substring(0, 100) + '...'
                  : suggestion.original_text
                }
              </div>
            </div>
          )}

          {/* AI suggestion */}
          {suggestion.replace_to && (
            <div className="mb-3">
              <p className="text-sm font-medium text-green-600 mb-1">💡 Suggestion:</p>
              
              {/* Confidence display */}
              <div className="flex items-center gap-2 mb-2 ml-4">
                <span className="text-xs text-gray-600">Confidence:</span>
                <div className="flex items-center gap-1">
                  <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-300 ${getConfidenceBarColor(suggestion.confidence)}`}
                      style={{ width: `${suggestion.confidence * 100}%` }}
                    />
                  </div>
                  <span className={`text-xs font-medium ${getConfidenceColor(suggestion.confidence)}`}>
                    {(suggestion.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              
              <div className="bg-white p-3 rounded border">
                <p className="text-sm text-gray-700 leading-relaxed font-mono">
                  {suggestion.replace_to}
                </p>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2 border-t">
            <button
              onClick={() => onAccept(suggestion.id)}
              className="flex-1 px-3 py-2 text-[10px] font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
              title="Accept suggestion and apply to document"
            >
              ✅ Accept
            </button>
            <button
              onClick={() => onCopy(suggestion.id)}
              className="flex-1 px-3 py-2 text-[10px] font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
              title="Copy suggestion content"
            >
              📋 Copy
            </button>
            <button
              onClick={() => onDismiss(suggestion.id)}
              className="flex-1 px-3 py-2 text-[10px] font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
              title="Dismiss this suggestion"
            >
              ❌ Dismiss
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default InlineSuggestionCard;