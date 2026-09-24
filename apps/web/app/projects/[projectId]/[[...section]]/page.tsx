import { Workspace } from "./workspace";
export default async function Page({params}:{params:Promise<{projectId:string;section?:string[]}>}) {
 const {projectId,section}=await params; return <Workspace projectId={projectId} section={section?.[0]??"policies"}/>;
}

