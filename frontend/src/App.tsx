import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import FileUpload from './components/FileUpload';
import Settings from './components/Settings';
import Sidebar from './components/Sidebar';
import ApiStatusIndicator from './components/ApiStatusIndicator';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [refreshKey, setRefreshKey] = useState(0);
  const [uploadCount, setUploadCount] = useState({ efatura: 0, bank: 0 });

  const handleUploadSuccess = (type: 'efatura' | 'bank') => {
    setUploadCount(prev => ({ ...prev, [type]: prev[type] + 1 }));
    setRefreshKey(prev => prev + 1);
  };


  return (
    <div className="App">
      <ApiStatusIndicator />
      <Sidebar 
        activeTab={activeTab} 
        onTabChange={setActiveTab}
        uploadCount={uploadCount}
      />
      
      <div className="main-content">
        <main className="App-main">
          {activeTab === 'dashboard' && (
            <Dashboard onNavigate={setActiveTab} />
          )}
          
          {activeTab === 'upload' && (
            <FileUpload 
              onUploadSuccess={handleUploadSuccess} 
              onNavigate={setActiveTab}
            />
          )}
          
          {activeTab === 'settings' && (
            <Settings />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;