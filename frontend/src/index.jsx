import React from 'react';
import ReactDOM from 'react-dom';

const App = () => {
  return (
    <div>
      <h3>React 组件已成功加载！</h3>
      <p>您可以在此处扩展更多前端交互功能。</p>
    </div>
  );
};

ReactDOM.render(<App />, document.getElementById('react-root'));
