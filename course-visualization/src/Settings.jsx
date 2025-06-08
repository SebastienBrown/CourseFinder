import React, { useState } from 'react';
import { getCurrentPort, updatePort } from './config';

export default function Settings({ onClose }) {
  const [port, setPort] = useState(getCurrentPort());
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    // Validate port number
    const portNum = parseInt(port);
    if (isNaN(portNum) || portNum < 1024 || portNum > 65535) {
      setError('Port must be a number between 1024 and 65535');
      return;
    }

    updatePort(portNum);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">API Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Port
            </label>
            <input
              type="number"
              value={port}
              onChange={(e) => setPort(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#3f1f69]"
              placeholder="Enter port number"
            />
            {error && (
              <p className="mt-1 text-sm text-red-600">{error}</p>
            )}
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-[#3f1f69] rounded-md hover:bg-[#5c3d8a] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#3f1f69]"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 