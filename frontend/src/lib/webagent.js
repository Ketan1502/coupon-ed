// Initialize a WebAgent instance and expose tools that call backend endpoints


export function createWebAgent({backendUrl, apiKey}){
// NOTE: this is a lightweight adapter — replace with real @google/generative-agents usage
async function uploadCouponTool({imageBase64, user_id}){
const res = await fetch(`${backendUrl}/api/upload-coupon`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ imageBase64, user_id })
})
return await res.json()
}


async function searchCouponsTool({query, user_id}){
const res = await fetch(`${backendUrl}/api/search?query=${encodeURIComponent(query)}&user_id=${encodeURIComponent(user_id)}`)
return await res.json()
}


return {
async sendMessage(user_id, text){
// naive agent logic: if text contains words like upload or screenshot, ask for image; else call search
const isSearch = !text.toLowerCase().includes('upload') && !text.toLowerCase().includes('screenshot')
if(isSearch){
return await searchCouponsTool({query: text, user_id})
}
return { error: 'UI should call upload tool with image' }
},
uploadCoupon: uploadCouponTool
}
}