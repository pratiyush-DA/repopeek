"""Comprehensive tests for RepoPeek universal polyglot parser engine and file classification."""

import pytest
from pathlib import Path

from repopeek.discovery.classifier import (
    EXTENSION_MAP,
    FileType,
    classify_file,
    is_sensitive_file,
)
from repopeek.models.schema import EdgeType
from repopeek.parsers.polyglot import (
    GO_CONFIG,
    JAVA_CONFIG,
    RUST_CONFIG,
    C_CONFIG,
    CPP_CONFIG,
    CSHARP_CONFIG,
    RUBY_CONFIG,
    PHP_CONFIG,
    SWIFT_CONFIG,
    LUA_CONFIG,
    ZIG_CONFIG,
    POWERSHELL_CONFIG,
    TERRAFORM_CONFIG,
    MARKDOWN_CONFIG,
    PolyglotTreeSitterParser,
)


def test_classifier_expansion():
    """Verify 36+ language extensions are mapped to recognized FileType enums."""
    assert classify_file(Path("main.go")) == FileType.GO
    assert classify_file(Path("lib.rs")) == FileType.RUST
    assert classify_file(Path("App.java")) == FileType.JAVA
    assert classify_file(Path("service.kt")) == FileType.KOTLIN
    assert classify_file(Path("Engine.scala")) == FileType.SCALA
    assert classify_file(Path("main.c")) == FileType.C
    assert classify_file(Path("main.cpp")) == FileType.CPP
    assert classify_file(Path("Program.cs")) == FileType.CSHARP
    assert classify_file(Path("script.rb")) == FileType.RUBY
    assert classify_file(Path("index.php")) == FileType.PHP
    assert classify_file(Path("view.swift")) == FileType.SWIFT
    assert classify_file(Path("mod.lua")) == FileType.LUA
    assert classify_file(Path("build.zig")) == FileType.ZIG
    assert classify_file(Path("deploy.ps1")) == FileType.POWERSHELL
    assert classify_file(Path("server.ex")) == FileType.ELIXIR
    assert classify_file(Path("node.erl")) == FileType.ERLANG
    assert classify_file(Path("math.f90")) == FileType.FORTRAN
    assert classify_file(Path("sim.jl")) == FileType.JULIA
    assert classify_file(Path("main.tf")) == FileType.TERRAFORM
    assert classify_file(Path("Token.sol")) == FileType.SOLIDITY
    assert classify_file(Path("docs.md")) == FileType.MARKDOWN
    assert classify_file(Path("Component.vue")) == FileType.VUE
    assert classify_file(Path("App.svelte")) == FileType.SVELTE


def test_sensitive_file_shielding():
    """Ensure sensitive credentials, private keys, and token files are shielded."""
    assert is_sensitive_file(Path(".env")) is True
    assert is_sensitive_file(Path(".env.production")) is True
    assert is_sensitive_file(Path("server.key")) is True
    assert is_sensitive_file(Path("id_rsa")) is True
    assert is_sensitive_file(Path("cert.pfx")) is True
    assert is_sensitive_file(Path(".npmrc")) is True
    assert is_sensitive_file(Path(".git-credentials")) is True

    # Templates must not be shielded
    assert is_sensitive_file(Path(".env.example")) is False
    assert is_sensitive_file(Path(".env.sample")) is False
    assert is_sensitive_file(Path(".env.template")) is False
    assert is_sensitive_file(Path("app.py")) is False


def test_go_polyglot_parsing():
    """Test Go struct and function extraction."""
    code = """package main

import "fmt"

type Server struct {
    port int
}

func StartServer(port int) {
    fmt.Println(port)
}
"""
    parser = PolyglotTreeSitterParser(GO_CONFIG)
    res = parser.parse_source(code, "server.go")
    assert res.is_success
    assert res.language == "go"

    node_sigs = [n.sig for n in res.nodes]
    assert any("Server" in s for s in node_sigs if s)
    assert any("StartServer" in s for s in node_sigs if s)


def test_rust_polyglot_parsing():
    """Test Rust struct and fn extraction."""
    code = """use std::collections::HashMap;

pub struct Config {
    pub timeout: u32,
}

pub fn initialize() {
    let map = HashMap::new();
}
"""
    parser = PolyglotTreeSitterParser(RUST_CONFIG)
    res = parser.parse_source(code, "src/lib.rs")
    assert res.is_success
    assert res.language == "rust"

    node_sigs = [n.sig for n in res.nodes]
    assert any("Config" in s for s in node_sigs if s)
    assert any("initialize" in s for s in node_sigs if s)


def test_java_polyglot_parsing():
    """Test Java class and method extraction."""
    code = """package com.example;

import java.util.List;

public class OrderService {
    public void processOrder() {
        System.out.println("Processing");
    }
}
"""
    parser = PolyglotTreeSitterParser(JAVA_CONFIG)
    res = parser.parse_source(code, "com/example/OrderService.java")
    assert res.is_success
    assert res.language == "java"

    node_sigs = [n.sig for n in res.nodes]
    assert any("OrderService" in s for s in node_sigs if s)
    assert any("processOrder" in s for s in node_sigs if s)


def test_cpp_polyglot_parsing():
    """Test C++ class and function extraction."""
    code = """#include <iostream>

class Engine {
public:
    void ignite() {
        std::cout << "Ignited" << std::endl;
    }
};

void runEngine() {
    Engine e;
}
"""
    parser = PolyglotTreeSitterParser(CPP_CONFIG)
    res = parser.parse_source(code, "engine.cpp")
    assert res.is_success
    assert res.language == "cpp"

    node_sigs = [n.sig for n in res.nodes]
    assert any("Engine" in s for s in node_sigs if s)
    assert any("runEngine" in s for s in node_sigs if s)


def test_csharp_polyglot_parsing():
    """Test C# class and method extraction."""
    code = """using System;

namespace Enterprise {
    public class BillingService {
        public void CalculateInvoice() {
            Console.WriteLine("Invoice calculated");
        }
    }
}
"""
    parser = PolyglotTreeSitterParser(CSHARP_CONFIG)
    res = parser.parse_source(code, "BillingService.cs")
    assert res.is_success
    assert res.language == "csharp"

    node_sigs = [n.sig for n in res.nodes]
    assert any("BillingService" in s for s in node_sigs if s)
    assert any("CalculateInvoice" in s for s in node_sigs if s)


def test_ruby_polyglot_parsing():
    """Test Ruby class and method extraction."""
    code = """require 'json'

class PaymentGateway
  def charge(amount)
    puts "Charging #{amount}"
  end
end
"""
    parser = PolyglotTreeSitterParser(RUBY_CONFIG)
    res = parser.parse_source(code, "gateway.rb")
    assert res.is_success
    assert res.language == "ruby"

    node_sigs = [n.sig for n in res.nodes]
    assert any("PaymentGateway" in s for s in node_sigs if s)
    assert any("charge" in s for s in node_sigs if s)


def test_markdown_doc_link_extraction():
    """Test Markdown section and cross-link extraction."""
    doc = """# Architecture Overview
This is the root document.
See the [Database Model](db_model.md) and [API Spec](api.md).
"""
    parser = PolyglotTreeSitterParser(MARKDOWN_CONFIG)
    res = parser.parse_source(doc, "README.md")
    assert res.is_success
    assert res.language == "markdown"
    link_targets = [e.dst for e in res.edges if e.type == EdgeType.IMPORTS]
    assert any("db_model.md" in t for t in link_targets)
    assert any("api.md" in t for t in link_targets)
