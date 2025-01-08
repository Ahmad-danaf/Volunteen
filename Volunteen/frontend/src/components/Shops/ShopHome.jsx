import React, { useEffect, useState } from 'react';
import { shopAPI } from '../../api/api'; 

const ShopHome = () => {
    const [shopData, setShopData] = useState(null); // State to store shop data
    const [loading, setLoading] = useState(true); // State to handle loading
    const [error, setError] = useState(null); // State to handle errors

    useEffect(() => {
        const fetchShopData = async () => {
            try {
                const response = await shopAPI.getShopHome(); // Fetch data using shopAPI
                setShopData(response.data); // Set the shop data in state
            } catch (err) {
                setError(err.response?.data?.error || 'An error occurred while fetching shop data.'); // Handle errors
            } finally {
                setLoading(false); // Set loading to false after API call
            }
        };

        fetchShopData(); // Call the function on component mount
    }, []);

    if (loading) {
        return <div>Loading shop data...</div>; // Show loading state
    }

    if (error) {
        return <div className="error">{error}</div>; // Show error message
    }

    return (
        <div className="shop-home">
            <h1>Shop: {shopData.shop.name}</h1>
            <p>Points Used This Month: {shopData.points_used_this_month}</p>
            <p>Points Left to Redeem: {shopData.points_left_to_redeem}</p>
        </div>
    );
};

export default ShopHome;
