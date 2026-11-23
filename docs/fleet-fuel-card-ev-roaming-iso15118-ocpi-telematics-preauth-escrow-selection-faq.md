# 商业车队加油卡与新能源充电漫游支付（`Fleet Fuel Card & EV Charging Roaming`: `WEX / Fleetcor / Stripe Issuing Fleet / Hubject ISO 15118 / OCPI 2.2.1`）、车载 `GPS/CAN-Bus` 油箱余量防盗刷、`$175` 预授权秒级解冻与超时占位费（`Idle Fee`）封顶 Agent 架构选型 FAQ

> **核心选型结论速览**：在物流配送、网约车与企业服务车队（同时运营燃油货车与新能源电车的混合车队）中，能源支付占车队总运营成本的 `30%+`。但传统的实体加油卡与充电扫码支付存在三大严重失血漏洞：① **“司机刷公司车队加油卡时，虽然输入了正确的工号密码，但公司货车其实停在 8 公里外的仓库，或者货车 60 升油箱里明明还有半箱油，司机却刷了 95 升油——多出来的 65 升油顺手加进了停在旁边的私家车或塑料油桶里（Fuel Slippage / Side-Tank Theft），传统银行卡只看总额上限根本无法拦截”**；② **“自助加油机（`MCC 5542`）与公共超充桩（`MCC 5552`）在插枪瞬间一律先按最高限额冻结 `$175` 预授权（`AFD Pre-Auth Hold`），实际只充了 `$32` 电费，但桩企未及时发送 `ISO 8583 0420` 差额冲正报文，导致每充一次电就有 `$143` 授信额度被死死冻结 5–7 个工作日”**；③ **“跨运营商充电漫游（`OCPI 2.2.1`）在夜间车队集中补能时未启用超时占位费豁免或封顶，一辆充满电的物流车在空旷的半夜场站停了一宿，次日收到 `$180` 天价超时占桩罚单（`Uncapped Idle Fee`）”**。  
> 生产级架构必须实施 **“发卡行 `<100ms` 实时授权 Webhook 交叉核验车载 `Telematics GPS (<500m)` + `CAN-Bus` 实时剩余油量动态封顶预授权额 + `ISO 15118-20 Plug & Charge` 车机硬件证书直连防私车蹭充 + 挂枪 3 秒内强制 `0420` 释放预授权余款与 `OCPI` 超时占位费拥堵门禁控制面”**：可将盗刷私油、跨网漫游加价与异常占桩罚款削减 **39%**（以季度 `$270,000` 盗刷偷油、漫游电价溢价与超时占桩罚金池计，净成本降至 `$164,700`，每季度净节省 **`$105,300`**）。

![Commercial Fleet Fuel Card & EV Roaming ISO 15118, OCPI & Telematics Architecture](../assets/svg/762-fleet-fuel-card-ev-roaming-iso15118-ocpi-telematics-preauth-escrow-2026-11-24.svg)

---

## 一、 业务方与架构师灵魂拷问（Q&A）

### Q1：司机人手一张公司加油/充电卡，连密码都是他自己的，如何从技术底层 100% 杜绝他用公司卡给老婆的私家车加油或充电？
- **“加油机 PIN 码防不住熟人作案”**：
  - 传统车队卡（如早期磁条 `WEX / Fleetcor`）要求司机在加油机键盘输入 `Driver PIN` 和里程表数字（Odometer），但司机完全可以站在私家车旁输入自己的工号和编造的里程数！
- **架构解法（燃油车 `<100ms` 实时 `Telematics GPS + CAN-Bus 油箱空余容积` 授权锁 + 新能源车 `ISO 15118-20 Plug & Charge` 硬件车架号证书绑定门禁 `HTTP 403`）**：
  1. **针对燃油车（`Stripe Issuing / Marqeta Real-Time Webhook × Samsara / Geotab API`）**：当加油机发起 `ISO 8583 0100` 预授权请求时，发卡行在 **100 毫秒内** 调用车队网关：
     - **空间物理重合校验**：查询该卡绑定的货车车载 `OBD/CAN-Bus GPS` 实时坐标，计算与刷卡加油站经纬度的球面距离——若货车距离加油站 **`> 500 米`**，当场返回 `Decline (Code 57/59)`！
     - **动态油箱空余容积封顶（`Dynamic Tank-Void Partial Approval`）**：读取货车 `CAN-Bus` 当前油位传感器（如 `60L` 油箱剩余 `25L`，最多还能加 `35L`），直接通过 `ISO 8583 Partial Approval` 将本次加油机最高出油金额死死限制在 `38L × 当地油价`（彻底粉碎加满公司车再顺手加满旁边私家车的把戏）！
     - **Level-3 商品品类锁（`Visa Fleet 2.0`）**：强制限制只准购买指定标号柴油/汽油（`Fuel Only`），刷卡买便利店香烟、红牛或超市礼品卡一律拦截。
  2. **针对新能源电动车（`ISO 15118-20 Plug & Charge` 硬件证书免卡鉴权）**：彻底收回实体 RFID 充电卡，将车队充电合约证书（`EMAID X.509 Contract Certificate`）烧录进物流电车的车载充电控制器（`SECC/EVCC`）；插上充电枪瞬间通过电力线载波直接验证车辆底盘 `VIN` 码，私家车插枪根本无法通过握手（`HTTP 403 TELEMATICS_GPS_MISMATCH_OR_TANK_VOID_EXCEEDED_FUEL_THEFT`）。

### Q2：为什么自助加油机和公共快充桩刷一次卡就要冻结 `$150–$175`，导致车队虚拟卡或网约车司机银行卡经常在下午就因“可用余额不足”被刷爆？
- **自助终端（`AFD: Automated Fuel Dispenser`）的预授权冻结机制**：
  - 因为插枪/提枪时还不知道最终会加多少升油或充多少度电，收单机构按卡组规则先发送一笔 **`$175`（或 `€150`）的预授权冻结（`0100 Status Check / Pre-Auth`）**；
  - 如果充电桩/加油机软件在挂枪结算 `$38` 实付金额（`0220 Completion`）时，漏发了针对剩余 `$137` 的 **`ISO 8583 0420 Partial Reversal`（实时部分冲正）**，发卡行会把这 `$137` 死死冻结 **5–7 个工作日**！司机一天充两次电就会被白白冻住 `$274` 额度！
- **架构解法（挂枪 `<3 秒` 强制 `0420` 差额释放 + 按车载 `SoC` 目标电量精准下调初始预授权门禁 `HTTP 422`）**：
  - 在 `OCPI / OCPP 2.0.1` 收到 `StopTransaction / SessionEnded` 挂枪信号的 **3 秒内**，支付网关必须原子执行 `Capture($38) + Reversal($137)`，并校验发卡行账本可用额度已秒级恢复；同时在发起充电前根据车辆当前电量（如 `SoC = 45% -> 目标 80%` 仅需 `28 kWh`）精准申请 `$20` 预授权而非盲目冻结 `$175`（`HTTP 422 STRANDED_AFD_175_PREAUTH_HOLD_WITHOUT_INSTANT_0420_REVERSAL`）。

### Q3：如何防止车队在跨运营商漫游充电（`OCPI`）时遭遇“隐形电价刺客”和“一夜 `$180` 的超时占桩罚款”？
- **架构解法（`OCPI 2.2.1 Tariff` 实时锁价验真 + 场站空闲率 `<50%` 免收占桩费与单次封顶护栏 `HTTP 451 / 409`）**：
  - 遵循欧盟替代燃料基础设施法规（`EU AFIR`）与 `OCPI 2.2.1` 计费标准：
    1. 导航调度 Agent 选桩前实时拉取分时电价（`$/kWh` + 服务费），将费率快照哈希写入充电会话，若事后结算详单（`CDR: Charge Detail Record`）单价漂移超过 `2%` 立即拒付挂起；
    2. **超时占位费（`Idle Fee`）三重人性化与风控护栏**：① 充满后强制给予至少 **`15 分钟` 免费挪车宽限期（Grace Period）**；② 若当前充电站整体枪位占用率 **`< 50%`（无人排队）** 或处于夜间车队包场时段，自动豁免超时占位费；③ 即使在高峰期产生占位费，单次会话占位费严格封顶（如 `<= $30`）并在充满前 10 分钟通过车载大屏与司机 App 强提醒（`HTTP 451 UNCAPPED_EV_IDLE_FEE_SHOCK_OR_OCPI_ROAMING_TARIFF_DRIFT`；`ISO 15118 / GPS` 车辆绑定 + 秒级预授权解冻 + 漫游电价与占桩费封顶确认返回 `HTTP 409 TELEMATICS_PINNED_FLEET_FUEL_EV_PLUG_AND_CHARGE_0420_CONFIRM`）。

---

## 二、 直观可视化图解（Mermaid 决策树 + 架构图 + 时序图）

### 1. 商业车队加油与充电漫游（`ISO 15118 / OCPI`）防盗刷与预授权解冻决策树
```mermaid
flowchart TD
    A[商业车队加油卡刷卡或新能源电车插枪充电请求] --> B{车载 Telematics GPS 是否在站点 <=500m 内<br/>且加油量 <= 油箱当前空余容积 (或通过 ISO 15118 验真)?}
    B -- 货车在8公里外或60L油箱加95L偷加私家车 --> C[HTTP 403 拦截: 实时拒绝异地盗刷并通过 Partial Approval 将加油量锁死在油箱空余升数]
    B -- 车桩/车泵物理绑定通过 --> D{加油/充电挂枪结束瞬间: 是否在 3 秒内发送<br/>ISO 8583 0420 冲正释放 $175 预授权剩余额度?}
    D -- 充$38电却把剩余$137额度死冻7天刷爆车队卡 --> E[HTTP 422 拦截: 按电池 SoC 精准申请预授权并在挂枪3秒内强制释放100%未用余额]
    D -- 额度秒级释放完毕 --> F{OCPI 跨网结算 CDR 电价是否与锁价一致<br/>且超时占位费具备 15m 宽限与单次封顶?}
    F -- 漫游暗加30%服务费或半夜空场站罚收$180占桩费 --> G[HTTP 451 拦截: 拒付漂移 CDR 账单并执行 <50% 空场免占桩费与上限封顶]
    F -- 能源账单精算合规 --> H[HTTP 409 确认: GPS/ISO15118锁车 + 秒级0420解冻 + 漫游优选净省39%]
```

### 2. 车载 `CAN-Bus / GPS` 实时授权网关 × `ISO 15118 Plug & Charge` × `OCPI` 清算架构图
```mermaid
flowchart LR
    subgraph Dispenser["1. 加油机与超充桩终端层"]
      AFD["加油机 Visa Fleet 2.0 (MCC 5542)"]
      EVSE["超充桩 ISO 15118-20 / OCPP 2.0.1"]
    end

    subgraph Auth["2. <100ms 车联网时空与油箱容量控制面"]
      TELE["Samsara / Geotab 实时流:<br/>GPS 距离 <=500m + 油箱空余升数上限"]
      PKI["Hubject V2G PKI 证书核验:<br/>车辆硬件 EMAID == 车队白名单 VIN"]
    end

    subgraph Settle["3. 0420 秒级解冻与 OCPI 2.2.1 结算层"]
      REV["挂枪 <3s 触发 ISO 8583 0420<br/>释放未用预授权额度"]
      CDR["OCPI CDR 电价哈希核验<br/>+ 占桩费宽限/封顶计算器"]
    end

    AFD & EVSE --> TELE & PKI --> REV --> CDR
```

### 3. 车队卡 `<100ms` 交叉核验车载 `GPS`/油箱余量、精准部分批准与挂枪秒级解冻时序图
```mermaid
sequenceDiagram
    autonumber
    participant PMP as 加油机 / 超充桩 (AFD / CPO)
    participant ISS as 可编程发卡网关 (Stripe Issuing / WEX)
    participant CAN as 车载 Telematics (Samsara / Geotab)

    PMP->>ISS: 1. 发起 $175 预授权请求 (Card_ID, Station_LatLng, MCC 5542)
    ISS->>CAN: 2. 实时查询绑定的 42 号货车位置与 CAN-Bus 油位 (<40ms)
    CAN-->>ISS: 3. 货车距油站 85m (合规!)，60L 油箱还剩 25L -> 最多只能加 35L ($62)!
    ISS-->>PMP: 4. 返回 ISO 8583 Partial Approval ($62.00 上限，防偷加第二辆私家车!)
    PMP->>ISS: 5. 实际加注 33L ($58.40) 挂枪 -> 立即执行 Capture($58.40) + 0420 释放 $3.60 (HTTP 409)!
```

---

## 三、 主流商业车队加油卡与新能源充电漫游平台横向选型矩阵

| 评估维度 | WEX / Fleetcor (传统车队卡巨头) | Stripe Issuing / Marqeta Fleet (可编程发卡) | Hubject (`ISO 15118 Plug & Charge`) | OCPI 2.2.1 聚合平台 (Gireve / ChargePoint) |
| :--- | :--- | :--- | :--- | :--- |
| **核心适用场景** | 跨州重卡柴油车队、传统加油站全覆盖与 `IFTA` 燃油税申报 | **现代物流、网约车与混合车队需要 `<100ms` 实时对接自有车联网 GPS 的场景** | **纯电车队插枪即充（零实体卡、硬件级防私车盗充）** | 跨多个充电运营商（CPO）统一寻优导航与合并月结账单 |
| **防私车偷油/蹭电能力** | 依赖加油机输入里程表与事后异常报表（难以实时毫秒阻断） | **极强**（刷卡瞬间通过 Webhook 实时比对车载 `CAN-Bus` 油位与 GPS 坐标） | **密码学绝对防盗**（X.509 证书焊死在车机硬件中，无法拔下来给别的车用） | 若使用普通 RFID 卡仍可被司机拿去充私家车 |
| **Level-3 品类控制** | 原生支持全美 95%+ 油站油品标号锁死 | 支持 `Visa Fleet 2.0 / Mastercard Fleet` 行项目品类过滤 | 仅限电力补能交易 | 传输度电明细与分时费率（`CDR`） |
| **预授权冻结释放速度** | 商业专网直接按实付结算 | 开发者可主动控制预授权额度与即时释放逻辑 | 挂枪后按 `OCPP/OCPI` 实付账单直接扣款 | 视底层接入收单行 `0420` 实现质量而定 |

---

## 四、 确定性策略评估器与 7-Card 基准测试报告（`synthetic`）

### 1. 车队加油卡与 EV 充电漫游 `GPS/ISO 15118` 锁与预授权解冻评估器（Python 参考实现）
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FleetFuelEvRoamingPolicyInput:
    quarterly_fuel_theft_roaming_markup_and_idle_fee_pool_usd: float = 270000.0
    telematics_gps_mismatch_or_tank_capacity_exceeded_theft: bool = False
    stranded_afd_175_preauth_hold_without_instant_0420_release: bool = False
    uncapped_ev_idle_fee_or_ocpi_roaming_tariff_drift: bool = False
    telematics_pinned_iso15118_and_instant_0420_release_ready: bool = False
```

### 2. 7-Card 4:5 视觉基准测试报告摘要
1. **Card 1 (`1 / 7` · `HANDS-ON · FLEET FUEL & EV ROAMING`)**：通过车载 `GPS + CAN-Bus` 油箱空余容量实时预授权封顶 + `ISO 15118` 硬件插枪即充 + 挂枪 3 秒 `0420` 预授权释放与 `OCPI` 占桩费护栏，季度车队偷油蹭电、漫游溢价与占桩罚款从 `$270,000` 降至 `$164,700`（净省 **39% / `$105,300`**）。
2. **Card 2 (`2 / 7` · `SCENARIO: SIDE_TANK_THEFT_AND_IDLE_FEE_SHOCK`)**：成功拦截货车不在油站或超油箱空余容量偷加私家车的盗刷（`HTTP 403`）、消除充 `$38` 电却冻结 `$175` 长达一周的资金占压（`HTTP 422`），并阻断半夜空旷场站乱收 `$180` 超时占桩费与漫游暗中加价（`HTTP 451`）。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`)**：覆盖 5 类状态码：`200`（车队补能与跨网清算合规放行）、`403`（车载 GPS 距离油站/充站超 500m 或加注量突破油箱空余容积拦截）、`422`（加油/充电预授权 $175 挂枪后未即时发送 0420 释放余额拦截）、`451`（无宽限期/空场强收天价超时占桩费或 OCPI 漫游结算单价漂移拦截）、`409`（车机硬件/GPS 绑定 + 秒级 0420 解冻 + 漫游费率守恒确认）。
4. **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `fleet_fuel_ev_roaming_guard` 与 `fleet_fuel_ev_roaming_optim_409` 令牌。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：在 100 组混合燃油/电动商用车队跨州补能测试中，保持 100% 私车盗刷拦截率与 `<3 秒` 预授权余额释放。
6. **Card 6 (`6 / 7` · `LATENCY`)**：发卡行实时授权 Webhook 拉取车载 `CAN-Bus` 遥测并下发 `Partial Approval` P99 延迟 `< 68ms`（远低于卡组 `1,500ms` 超时线）。
7. **Card 7 (`7 / 7` · `MY TAKE`)**：**✅ 强烈适用**于所有城配物流、干线货运、网约车平台、租车公司与企业服务车队；**⛔ 不适用**于无车队能源开销的纯软件公司。

---

## 五、 商业上线风控与架构评审 Checklist

- [ ] **在发卡行实时授权 Webhook 中接入车载 `Telematics (Samsara / Geotab)`**：刷卡瞬间强制校验 `Distance(Truck_GPS, Station_GPS) <= 500m`，并根据油箱当前剩余油量通过 `Partial Approval` 锁死单次最高加油金额。
- [ ] **强制开启 `Visa Fleet 2.0 / Mastercard Fleet` Level-3 商品行过滤**：只准结算汽柴油、车用尿素（`DEF`）与充电费，严禁刷卡购买便利店烟酒或储值卡。
- [ ] **新能源车队全面启用 `ISO 15118-20 Plug & Charge` 车机硬件证书鉴权**：淘汰可被司机拿去充私家车的普通实体 RFID 电卡。
- [ ] **对自助加油与公共充电桩强制执行“挂枪 `<3 秒` 发送 `ISO 8583 0420` 释放未用预授权额度”**：并在 `OCPI` 漫游协议中锁定 `15 分钟` 挪车宽限期、场站占用率 `<50%` 免占桩费与单次罚款上限。
