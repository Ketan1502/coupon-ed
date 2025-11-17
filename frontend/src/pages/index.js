import React, {useState} from 'react'
import { createWebAgent } from '../lib/webagent'


export default function Home(){
const [userId] = useState('demo-user-1')
const [log, setLog] = useState([])
const [query, setQuery] = useState('')
const agent = createWebAgent({ backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL })


async function handleSearch(e){
e.preventDefault()
const resp = await agent.sendMessage(userId, query)
setLog(prev => [...prev, {direction: 'user', text: query}, {direction: 'bot', text: JSON.stringify(resp)}])
setQuery('')
}


async function handleUpload(ev){
const file = ev.target.files[0]
const reader = new FileReader()
reader.onload = async ()=>{
const base64 = reader.result.split(',')[1]
const resp = await agent.uploadCoupon({ imageBase64: base64, user_id: userId })
setLog(prev => [...prev, {direction:'user', text:'[uploaded image]'}, {direction:'bot', text: 'Saved: '+resp.coupon_id}])
}
reader.readAsDataURL(file)
}


return (
<div style={{padding:20}}>
<h1>Coupon-ed — Web Agent (Demo)</h1>
<div>
<input type="file" accept="image/*" onChange={handleUpload} />
</div>


<form onSubmit={handleSearch} style={{marginTop:20}}>
<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search coupons (eg. spectacles under ₹500)" style={{width:'60%'}} />
<button type="submit">Search</button>
</form>


<div style={{marginTop:20}}>
{log.map((m,i)=> (
<div key={i}><b>{m.direction}</b>: {m.text}</div>
))}
</div>
</div>
)
}