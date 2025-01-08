import React, { useState, useEffect } from 'react';
import { childAPI } from '../../api/api.js'; // Import childAPI from api.js

const ChildActiveTasks = () => {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTasks = async () => {
            try {
                const response = await childAPI.getActiveTasks();
                setTasks(response.data.tasks); // Assuming the API response contains "tasks"
            } catch (err) {
                setError('Failed to fetch active tasks. Please try again later.');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchTasks();
    }, []);

    if (loading) {
        return <div>Loading active tasks...</div>;
    }

    if (error) {
        return <div className="error">{error}</div>;
    }

    return (
        <div className="child-active-tasks">
            <h1>Active Tasks</h1>
            {tasks.length === 0 ? (
                <p>No active tasks found.</p>
            ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ backgroundColor: '#007bff', color: 'white' }}>
                            <th style={{ padding: '8px', textAlign: 'left' }}>Task Title</th>
                            <th style={{ padding: '8px', textAlign: 'left' }}>Deadline</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tasks.map((task, index) => (
                            <tr key={index} style={{ borderBottom: '1px solid #ddd' }}>
                                <td style={{ padding: '8px' }}>{task.title}</td>
                                <td style={{ padding: '8px' }}>{task.deadline}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

export default ChildActiveTasks;
