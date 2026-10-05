"""Unit tests for RepoPeek TypeScript & JavaScript AST Parser and Resolution."""

from pathlib import Path
import pytest

from repopeek.discovery.classifier import FileType, classify_file
from repopeek.graph.builder import GraphBuilder
from repopeek.models.schema import Confidence, EdgeType
from repopeek.parsers.typescript import TypeScriptParser


# ---------------------------------------------------------------------------
# Test 1: Imports, Interfaces, and Types
# ---------------------------------------------------------------------------

def test_typescript_parser_imports_and_types():
    source = """/**
 * User types and service contracts
 */
import { User, UserRole as Role } from './models';
import axios from 'axios';
import type { Config } from '../config';
const logger = require('./logger');

export interface BaseEntity {
  id: string;
  createdAt: Date;
}

export interface UserAccount extends BaseEntity {
  username: string;
  email: string;
}

export type AccountStatus = "active" | "suspended" | "pending";
"""
    parser = TypeScriptParser()
    res = parser.parse_source(source, rel_path="src/types.ts")
    assert res.is_success
    assert res.language == "typescript"

    # Module node
    mod_node = next(n for n in res.nodes if n.kind == "file")
    assert mod_node.id == "ts:src/types.ts::<module>"
    assert "User types and service contracts" in mod_node.story.text

    # Verify imports
    import_dsts = [e.dst for e in res.edges if e.type == EdgeType.IMPORTS]
    assert "./models" in import_dsts
    assert "./models.User" in import_dsts
    assert "./models.UserRole" in import_dsts
    assert "axios" in import_dsts
    assert "../config" in import_dsts
    assert "./logger" in import_dsts

    # Interfaces
    base_iface = next(n for n in res.nodes if n.kind == "interface" and "BaseEntity" in n.id)
    assert base_iface.sig == "interface BaseEntity"
    assert base_iface.span.start == 9
    assert base_iface.span.end == 12

    user_iface = next(n for n in res.nodes if n.kind == "interface" and "UserAccount" in n.id)
    assert user_iface.sig == "interface UserAccount"

    # Interface extension edge
    inherits_edge = next(e for e in res.edges if e.src == user_iface.id and e.type == EdgeType.INHERITS)
    assert inherits_edge.dst == "BaseEntity"

    # Type alias
    type_node = next(n for n in res.nodes if n.kind == "type")
    assert type_node.sig == "type AccountStatus"


# ---------------------------------------------------------------------------
# Test 2: Classes, Methods, Constructors, and Inheritance
# ---------------------------------------------------------------------------

def test_typescript_parser_classes_and_methods():
    source = """import { BaseService } from './base';

export class UserService extends BaseService implements IUserService {
  private apiUrl: string;

  constructor(apiUrl: string) {
    super();
    this.apiUrl = apiUrl;
  }

  /**
   * Fetches user details by ID
   */
  async getUser(userId: string): Promise<User> {
    if (!userId) {
      throw new InvalidArgumentError("userId required");
    }
    const response = await fetch(`${this.apiUrl}/users/${userId}`);
    return response.json();
  }
}
"""
    parser = TypeScriptParser()
    res = parser.parse_source(source, rel_path="src/services/user.ts")
    assert res.is_success

    # Class node
    class_node = next(n for n in res.nodes if n.kind == "class")
    assert class_node.id == "ts:src/services/user.ts::UserService"
    assert "extends BaseService" in class_node.sig

    # Class inheritance & implements
    inherits_edge = next(e for e in res.edges if e.src == class_node.id and e.type == EdgeType.INHERITS)
    assert inherits_edge.dst == "BaseService"

    implements_edge = next(e for e in res.edges if e.src == class_node.id and e.type == EdgeType.IMPLEMENTS)
    assert implements_edge.dst == "IUserService"

    # Constructor method
    ctor_node = next(n for n in res.nodes if n.kind == "method" and "constructor" in n.id)
    assert ctor_node.facts.params == ["apiUrl"]

    # Method getUser
    method_node = next(n for n in res.nodes if n.kind == "method" and "getUser" in n.id)
    assert method_node.facts.params == ["userId"]
    assert method_node.facts.returns == "Promise<User>"
    assert method_node.facts.raises == ["InvalidArgumentError"]
    assert "Fetches user details by ID" in method_node.story.text
    assert method_node.facts.complexity >= 2

    # Method calls
    method_calls = [e.dst for e in res.edges if e.src == method_node.id and e.type == EdgeType.CALLS]
    assert "fetch" in method_calls or "response.json" in method_calls


# ---------------------------------------------------------------------------
# Test 3: Standalone Functions and Arrow Functions
# ---------------------------------------------------------------------------

def test_typescript_parser_functions_and_arrows():
    source = """/**
 * Calculates discount price based on tier
 */
export function calculateDiscount(price: number, tier: string): number {
  if (tier === 'VIP') {
    return price * 0.8;
  } else if (tier === 'MEMBER') {
    return price * 0.9;
  }
  return price;
}

export const formatCurrency = (amount: number, currency: string = "USD"): string => {
  return `${currency} ${amount.toFixed(2)}`;
};

export const isFree = (amount: number): boolean => amount <= 0;
"""
    parser = TypeScriptParser()
    res = parser.parse_source(source, rel_path="src/utils/pricing.ts")
    assert res.is_success

    # Standalone function
    calc_func = next(n for n in res.nodes if n.id == "ts:src/utils/pricing.ts::calculateDiscount")
    assert calc_func.facts.params == ["price", "tier"]
    assert calc_func.facts.returns == "number"
    assert calc_func.facts.complexity >= 3
    assert "Calculates discount price" in calc_func.story.text

    # Arrow function with block body
    fmt_func = next(n for n in res.nodes if n.id == "ts:src/utils/pricing.ts::formatCurrency")
    assert fmt_func.facts.params == ["amount", "currency"]
    assert fmt_func.facts.returns == "string"

    # Arrow function with expression body
    free_func = next(n for n in res.nodes if n.id == "ts:src/utils/pricing.ts::isFree")
    assert free_func.facts.params == ["amount"]
    assert free_func.facts.returns == "boolean"


# ---------------------------------------------------------------------------
# Test 4: JavaScript and JSX React Components
# ---------------------------------------------------------------------------

def test_javascript_and_jsx_parser():
    source = """import React, { useState } from 'react';

export function UserButton({ label, onClick }) {
  const [clicked, setClicked] = useState(false);

  const handleClick = () => {
    setClicked(true);
    onClick();
  };

  return (
    <button onClick={handleClick}>
      {label} - {clicked ? 'Active' : 'Idle'}
    </button>
  );
}
"""
    parser = TypeScriptParser()
    res = parser.parse_source(source, rel_path="src/components/UserButton.jsx")
    assert res.is_success
    assert res.language == "javascript"

    # Module node has js prefix
    mod_node = next(n for n in res.nodes if n.kind == "file")
    assert mod_node.id == "js:src/components/UserButton.jsx::<module>"

    # Function component
    btn_node = next(n for n in res.nodes if n.id == "js:src/components/UserButton.jsx::UserButton")
    assert btn_node.kind == "function"

    # Arrow handler inside or defined
    calls = [e.dst for e in res.edges if e.type == EdgeType.CALLS]
    assert "useState" in calls


# ---------------------------------------------------------------------------
# Test 5: File Classifier Integration
# ---------------------------------------------------------------------------

def test_file_classifier_typescript_and_javascript():
    assert classify_file(Path("src/index.ts")) == FileType.TYPESCRIPT
    assert classify_file(Path("src/App.tsx")) == FileType.TYPESCRIPT
    assert classify_file(Path("src/utils.js")) == FileType.JAVASCRIPT
    assert classify_file(Path("src/Component.jsx")) == FileType.JAVASCRIPT
    assert classify_file(Path("src/bundle.mjs")) == FileType.JAVASCRIPT
    assert classify_file(Path("src/config.cjs")) == FileType.JAVASCRIPT


# ---------------------------------------------------------------------------
# Test 6: GraphBuilder & Cross-File Symbol Resolution
# ---------------------------------------------------------------------------

def test_graph_builder_cross_file_ts_resolution():
    api_source = """export async function fetchUserData(userId: string): Promise<any> {
  const res = await fetch(`/api/users/${userId}`);
  return res.json();
}
"""
    client_source = """import { fetchUserData } from './api';

export async function renderProfile(userId: string) {
  const user = await fetchUserData(userId);
  return user;
}
"""
    parser = TypeScriptParser()
    res_api = parser.parse_source(api_source, rel_path="src/api.ts")
    res_client = parser.parse_source(client_source, rel_path="src/client.ts")

    builder = GraphBuilder()
    graph = builder.build([res_api, res_client])

    # Check that both nodes exist
    assert "ts:src/api.ts::fetchUserData" in graph.nodes
    assert "ts:src/client.ts::renderProfile" in graph.nodes

    # Check CALLS edge from renderProfile to fetchUserData
    call_edges = [
        e for e in graph.edges
        if e.src == "ts:src/client.ts::renderProfile" and e.type == EdgeType.CALLS
    ]
    assert len(call_edges) >= 1
    edge = call_edges[0]
    assert edge.dst == "ts:src/api.ts::fetchUserData"
    assert edge.confidence == Confidence.RESOLVED
