import React, { useCallback, useEffect } from 'react';
import {
    ReactFlow,
    useNodesState,
    useEdgesState,
    addEdge,
    ConnectionLineType,
    Panel,
    Handle,
    Position,
    Background,
    Controls,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { Monitor, Server, Database, Brain, Shield } from 'lucide-react';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

// -----------------------------------------------------
// CUSTOM NODES
// -----------------------------------------------------
const BaseNode = ({ data, children, bgClass, borderClass, icon: Icon, title }) => (
    <div className={`px-4 py-3 shadow-md rounded-md bg-white border-2 ${borderClass} min-w-[150px]`}>
        <Handle type="target" position={Position.Top} className="w-2 h-2" />
        <div className="flex items-center gap-2 mb-2">
            <div className={`p-1.5 rounded-md ${bgClass} text-white`}>
                <Icon size={16} />
            </div>
            <div className="font-bold text-sm text-gray-800">{title}</div>
        </div>
        <div className="text-sm font-semibold text-gray-900">{data.label}</div>
        {data.tech && <div className="text-xs text-gray-500 mt-1">{data.tech}</div>}
        <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </div>
);

const FrontendNode = ({ data }) => (
    <BaseNode data={data} title="Frontend" icon={Monitor} bgClass="bg-blue-500" borderClass="border-blue-200" />
);

const BackendNode = ({ data }) => (
    <BaseNode data={data} title="Backend" icon={Server} bgClass="bg-green-500" borderClass="border-green-200" />
);

const DataNode = ({ data }) => (
    <BaseNode data={data} title="Data" icon={Database} bgClass="bg-yellow-500" borderClass="border-yellow-200" />
);

const AINode = ({ data }) => (
    <BaseNode data={data} title="AI" icon={Brain} bgClass="bg-purple-500" borderClass="border-purple-200" />
);

const SecurityNode = ({ data }) => (
    <BaseNode data={data} title="Security" icon={Shield} bgClass="bg-slate-500" borderClass="border-slate-200" />
);

const nodeTypes = {
    frontend: FrontendNode,
    backend: BackendNode,
    data: DataNode,
    ai: AINode,
    security: SecurityNode,
};

// -----------------------------------------------------
// LAYOUT ALGORITHM
// -----------------------------------------------------
const nodeWidth = 200;
const nodeHeight = 100;

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
    const isHorizontal = direction === 'LR';
    dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 100 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const newNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        const newNode = {
            ...node,
            targetPosition: isHorizontal ? 'left' : 'top',
            sourcePosition: isHorizontal ? 'right' : 'bottom',
            position: {
                x: nodeWithPosition.x - nodeWidth / 2,
                y: nodeWithPosition.y - nodeHeight / 2,
            },
        };
        return newNode;
    });

    return { nodes: newNodes, edges };
};

// -----------------------------------------------------
// MAIN COMPONENT
// -----------------------------------------------------
const ReactFlowDiagram = ({ data }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    useEffect(() => {
        if (data && data.nodes && data.edges) {
            // Map edges to look nice
            const formattedEdges = data.edges.map(edge => ({
                ...edge,
                type: 'smoothstep',
                animated: true,
                style: { stroke: '#94a3b8', strokeWidth: 2 },
                labelStyle: { fill: '#475569', fontWeight: 500, fontSize: 11 },
                labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.8 },
            }));

            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
                data.nodes,
                formattedEdges
            );
            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        }
    }, [data]);

    const onConnect = useCallback(
        (params) =>
            setEdges((eds) =>
                addEdge({ ...params, type: ConnectionLineType.SmoothStep, animated: true }, eds)
            ),
        []
    );

    if (!data || !data.nodes || data.nodes.length === 0) {
        return (
            <div className="flex items-center justify-center min-h-[400px] w-full bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center text-gray-500">
                No architecture data available for rendering.
            </div>
        );
    }

    return (
        <div className="w-full h-[600px] bg-white border border-gray-200 rounded-lg overflow-hidden shadow-inner">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                connectionLineType={ConnectionLineType.SmoothStep}
                fitView
                attributionPosition="bottom-left"
            >
                <Background color="#ccc" gap={16} />
                <Controls />
                <Panel position="top-right" className="bg-white/80 backdrop-blur p-2 rounded shadow text-xs font-semibold text-gray-600 border border-gray-200">
                    Interactive Architecture
                </Panel>
            </ReactFlow>
        </div>
    );
};

export default ReactFlowDiagram;
