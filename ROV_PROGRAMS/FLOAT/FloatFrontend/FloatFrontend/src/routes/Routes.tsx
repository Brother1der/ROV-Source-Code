import { BrowserRouter, Routes, Route} from "react-router-dom";
import Home from '../home.tsx';
import DataScreen from "../data.tsx";

export default function MainRoutes() {
 return (
   <BrowserRouter>
     <Routes>
       <Route path="/" element={<Home />} />
       <Route path="/data" element={<DataScreen/>} />
       <Route path="/contact" element={<Home />} />
     </Routes>
   </BrowserRouter>
 );
}