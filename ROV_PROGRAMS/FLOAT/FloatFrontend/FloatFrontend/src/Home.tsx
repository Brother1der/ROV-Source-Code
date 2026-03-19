import { Link } from "react-router-dom";

export default function Home() {
    return (
        <div>
            <h1>Welcome to the Home Page</h1>
            <p>This is the main landing page of the application.</p>
            <Link to="/data">Go to Data Screen</Link>
        </div>
    );
}