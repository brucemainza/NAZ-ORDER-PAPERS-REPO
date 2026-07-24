export function SimilarityScore({ score }) {
    const tone = score > 80 ? "similarity-score__fill--high" : score >= 50 ? "similarity-score__fill--medium" : "similarity-score__fill--low";
    return (<div className="similarity-score">
      <div className="similarity-score__label-row">
        <span>Similarity</span>
        <span className="similarity-score__value">{score}%</span>
      </div>
      <div className="similarity-score__track">
        <div className={`similarity-score__fill ${tone}`} style={{ width: `${score}%` }}/>
      </div>
    </div>);
}
