import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import qs from 'qs';
const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();
    
  
    const handleLogin = async (e) => {
        e.preventDefault();
        console.log('Logging in...');
        console.log('Username:', username);
        console.log('url:', `${import.meta.env.VITE_API_URL}/token/`);
        console.log('API Key:', import.meta.env.VITE_API_KEY);
        let data = qs.stringify({
        'username': username,
        'password': password 
        });

        let config = {
        method: 'post',
        maxBodyLength: Infinity,
        url: 'http://localhost:8000/api/token/',
        headers: { 
            'X-API-Key': import.meta.env.VITE_API_KEY,
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        data : data
        };

        axios.request(config)
        .then((response) => {
        console.log(JSON.stringify(response.data));
        })
        .catch((error) => {
        console.log(error);
        });

    };

    return (
        <div className="login-container">
            <nav className="navbar navbar-expand-lg">
                <a className="navbar-brand" href="/">Volunteen</a>
            </nav>

            <div className="login-card">
                <h1 className="login-header">Welcome to <span className="orange-text">Volunteen</span></h1>
                {error && <div className="alert alert-danger">{error}</div>}
                <form onSubmit={handleLogin}>
                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input
                            type="text"
                            id="username"
                            className="form-control"
                            placeholder="Enter your username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            className="form-control"
                            placeholder="Enter your password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className="btn btn-primary btn-block">Login</button>
                </form>
                <img src="/static/images/logo.png" alt="Volunteen Logo" className="login-logo" />
            </div>
        </div>
    );
};

export default Login;
