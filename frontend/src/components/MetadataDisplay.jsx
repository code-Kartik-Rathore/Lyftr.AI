import './MetadataDisplay.css'

function MetadataDisplay({ metadata }) {
  const isCache = metadata.resolution_source === 'LLM_CACHE'

  return (
    <div className="metadata">
      <span
        className={`meta-badge ${isCache ? 'cache' : 'live'}`}
        data-testid="meta-source"
      >
        {metadata.resolution_source}
      </span>
      <span className="meta-item" data-testid="meta-model">
        {metadata.model}
      </span>
      <span className="meta-item" data-testid="meta-latency">
        {metadata.latency_ms} ms
      </span>
      <span className="meta-item" data-testid="meta-input-tokens">
        {metadata.input_tokens}
      </span>
      <span className="meta-item" data-testid="meta-output-tokens">
        {metadata.output_tokens}
      </span>
    </div>
  )
}

export default MetadataDisplay
