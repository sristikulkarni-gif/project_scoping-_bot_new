// src/api/presentonApi.js
import api from "./axiosClient";

/**
 * Check Presenton service health
 */
export const checkPresentonHealth = async () => {
    const response = await api.get("/presenton/health");
    return response.data;
};

/**
 * Generate presentation from project scope using Presenton
 * @param {string} projectId - UUID of the project
 * @param {number} nSlides - Number of slides to generate (default: 10)
 * @param {string} template - Template name (default: "general")
 */
export const generateWithPresenton = async (projectId, nSlides = 10, template = "general") => {
    const response = await api.post(`/presenton/generate/${projectId}`, null, {
        params: { n_slides: nSlides, template }
    });
    return response.data;
};

/**
 * Get Presenton information
 */
export const getPresentonInfo = async () => {
    const response = await api.get("/presenton/info");
    return response.data;
};
